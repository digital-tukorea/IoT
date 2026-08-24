"""
vision_module.py
YOLO 객체 탐지(★ 4클래스: 작물 종류만) + RGB(HSV) 기반 익음도 계산 +
★ 색상 기반 병해충 1차 판단 + 시간에 따른 색상 변화 추적(보조 신호)을 캡슐화한다.

다른 모듈(mqtt_module, upload_module, motion_module)은 이 모듈의 존재를
전혀 모르며, main_controller가 detect()의 반환값만 받아서 나머지 모듈에 전달한다.

전제: 카메라가 고정된 것이 아니라 "로봇이 농원을 돌아다니며" 촬영한다.
  같은 개체 식별에는 화면 픽셀 위치 대신 구역(zone_id) + 구역 내 좌->우 순번을 쓴다.
"""

import re
import json
from dataclasses import dataclass
from typing import Optional
from collections import deque

import cv2
import numpy as np
from ultralytics import YOLO


# ── ★ Kindwise API가 영어로 반환하는 병명을 한국어로 옮기기 위한 사전 ──
# API의 language 파라미터로 한국어 응답을 우선 시도하지만(diagnose_disease_type
# 참고), 지원이 확실하지 않아 이 사전을 확실한 안전장치(fallback)로 둔다.
# 키는 소문자 기준으로 매칭한다. 여기 없는 병명은 영문 원본을 그대로 반환한다.
# ⚠️ 국내 농업 현장에서 통용되는 명칭 기준으로 구성했으나, 실제 병징과
# 완전히 일치하는지는 전문가 검수를 권장한다. 새로운 병명이 나오면 계속 추가할 것.
DISEASE_NAME_KO = {
    "botrytis": "잿빛곰팡이병",
    "grey mold": "잿빛곰팡이병",
    "gray mold": "잿빛곰팡이병",
    "anthracnose": "탄저병",
    "powdery mildew": "흰가루병",
    "downy mildew": "노균병",
    "fusarium": "시들음병(푸사리움)",
    "fusarium wilt": "시들음병(푸사리움)",
    "bacterial spot": "세균성점무늬병",
    "bacterial wilt": "세균성시들음병",
    "bacterial blight": "세균성마름병",
    "leaf spot": "잎반점병",
    "leaf blight": "잎마름병",
    "early blight": "겹무늬병",
    "late blight": "역병",
    "canker": "궤양병",
    "rust": "녹병",
    "mosaic virus": "모자이크바이러스병",
    "mosaic": "모자이크바이러스병",
    "fruit rot": "열매썩음병",
    "root rot": "뿌리썩음병",
    "wilt": "시들음병",
    "scab": "더뎅이병",
    "black rot": "검은썩음병",
    "sooty mold": "그을음병",
    "verticillium": "시들음병(버티실리움)",
    "verticillium wilt": "시들음병(버티실리움)",
    "rhizoctonia": "잘록병",
    "sclerotinia": "균핵병",
    "alternaria": "겹무늬병(알터나리아)",
    "nutrient deficiency": "영양결핍",
    "abiotic": "비생물적 스트레스(환경요인)",
    "pest damage": "해충피해",
    "aphids": "진딧물",
    "spider mites": "응애",
    "thrips": "총채벌레",
    "whitefly": "가루이",
}


def translate_disease_name(english_name):
    """영문 병명(원문)을 한국어로 변환. 사전에 없으면 원문을 그대로 반환."""
    if not english_name:
        return english_name
    return DISEASE_NAME_KO.get(english_name.strip().lower(), english_name)


@dataclass
class DetectionResult:
    """탐지 1건의 표준화된 결과. 다른 모듈은 이 형태로만 데이터를 주고받는다."""
    crop_id: str
    confidence: float
    ripeness_percent: Optional[float]           # 이번 캡처 스냅샷 기준 익음도
    ripeness_percent_smoothed: Optional[float]   # 최근 이력 평균 익음도 (더 안정적)
    is_ripe: bool
    disease_detected: bool                       # ★ 색상 분석 기반 1차 판단 (더 이상 YOLO 아님)
    box_bgr: np.ndarray
    track_id: Optional[str] = None
    color_change_alert: bool = False             # 색상 급변 조기경보 (보조 신호)
    disease_type: Optional[str] = None
    diagnosis_trigger: Optional[str] = None       # "color" / "color_change" / "both"

    @property
    def growth_status(self):
        """★ 서버 문서 규격: 문자열 단계가 아니라 소수점 1자리 퍼센티지 문자열 (예: "67.3")."""
        if self.ripeness_percent_smoothed is None:
            return "0.0"
        return f"{round(self.ripeness_percent_smoothed, 1)}"

    @property
    def health_status(self):
        """★ 서버 문서 표기 그대로: 병="disease"(소문자), 정상="NORMAL"(대문자)."""
        return "disease" if self.disease_detected else "NORMAL"

    @property
    def needs_attention(self):
        return self.disease_detected or self.color_change_alert


class _Track:
    """구역(zone_id) + 작물명 + 구역 내 순번을 기준으로 같은 개체를 추적."""
    def __init__(self, track_id, zone_id, crop_name, slot_index, history_window):
        self.track_id = track_id
        self.zone_id = zone_id
        self.crop_name = crop_name
        self.slot_index = slot_index
        self.progress_history = deque(maxlen=history_window)
        self.abnormal_ratio_history = deque(maxlen=history_window)
        self.last_seen_zone_visit = 0


class VisionModule:
    def __init__(self, config, crop_color_profiles):
        self.config = config
        self.crop_color_profiles = crop_color_profiles
        self.model = YOLO(config["model_path"])
        self.id_to_crop = self._load_class_lookup(config["class_map_path"])
        self.imgsz = config.get("imgsz", 640)

        # ── 색상 변화 추적 상태 (구역 기반) ──
        self.tracks = {}
        self._next_track_id = 0
        self.zone_visit_count = {}

        ct_cfg = config.get("color_tracking", {})
        self.history_window = ct_cfg.get("history_window", 5)
        self.sudden_change_threshold = ct_cfg.get("sudden_change_abnormal_ratio_delta", 0.15)
        self.min_samples_for_alert = ct_cfg.get("min_samples_for_alert", 2)
        self.track_expire_visits = ct_cfg.get("track_expire_visits", 3)

    # ── class_map.json -> class_id별 작물명 매핑 ──────────────
    # ★ 4클래스 체계: 접미사(_healthy/_diseased) 없이 작물명 그대로가 정상 형태.
    def _load_class_lookup(self, class_map_path):
        with open(class_map_path, "r", encoding="utf-8") as f:
            class_map = json.load(f)

        # 혹시 예전 7클래스 class_map을 실수로 넣은 경우까지 방어적으로 처리
        # (있어도 문제없이 작물명만 뽑아서 4클래스처럼 동작하게 함)
        pattern = re.compile(r"^(?P<crop>.+?)_(?:healthy|diseased)$")
        id_to_crop = {}
        for key, class_id in class_map.items():
            m = pattern.match(key)
            crop_name = m.group("crop") if m else key
            id_to_crop[class_id] = crop_name

        return id_to_crop

    # ── HSV 기반 익음도 진행도(progress) + 이상색상비율 분석 ────────
    def _analyze_fruit_color(self, roi_bgr, profile):
        if roi_bgr.size == 0:
            return None

        sample_size = self.config["sample_size"]
        roi_small = cv2.resize(roi_bgr, (sample_size, sample_size), interpolation=cv2.INTER_AREA)
        hsv = cv2.cvtColor(roi_small, cv2.COLOR_BGR2HSV).astype(np.float32)
        h, s = hsv[:, :, 0], hsv[:, :, 1]

        hue_start, hue_end = profile["hue_start"], profile["hue_end"]
        direction, margin, min_sat = profile["direction"], profile["margin"], profile["min_saturation"]

        end_shifted = ((hue_end - hue_start) * direction) % 180
        if end_shifted == 0:
            end_shifted = 180

        progress = (((h - hue_start) * direction) % 180) / end_shifted
        on_path = (progress >= -margin) & (progress <= 1 + margin)
        normal_mask = on_path & (s >= min_sat)
        abnormal_ratio = float((~normal_mask).mean())

        mean_progress = float(np.clip(progress[normal_mask], 0, 1).mean()) if normal_mask.sum() > 0 else None
        return {"progress": mean_progress, "abnormal_ratio": abnormal_ratio}

    # ── ★ 색상 기반 병해충 1차 판단 ──
    def _classify_disease_by_color(self, abnormal_ratio, profile):
        threshold = profile.get("disease_threshold")
        if threshold is None:
            return False
        return abnormal_ratio > threshold

    # ── 같은 개체 매칭 ──
    def _match_or_create_track(self, zone_id, crop_name, slot_index):
        track_key = (zone_id, crop_name, slot_index)

        for track in self.tracks.values():
            if (track.zone_id, track.crop_name, track.slot_index) == track_key:
                track.last_seen_zone_visit = self.zone_visit_count[zone_id]
                return track

        track_id = f"{zone_id}_{crop_name}_{slot_index}_{self._next_track_id}"
        self._next_track_id += 1
        new_track = _Track(track_id, zone_id, crop_name, slot_index, self.history_window)
        new_track.last_seen_zone_visit = self.zone_visit_count[zone_id]
        self.tracks[track_id] = new_track
        return new_track

    def _assign_slot_indices(self, boxes_with_info):
        groups = {}
        for item in boxes_with_info:
            groups.setdefault(item["crop_name"], []).append(item)

        for crop_name, items in groups.items():
            items.sort(key=lambda it: it["x1"])
            for idx, it in enumerate(items):
                it["slot_index"] = idx

        return boxes_with_info

    def _prune_stale_tracks(self):
        stale_ids = []
        for tid, t in self.tracks.items():
            current_visit = self.zone_visit_count.get(t.zone_id, t.last_seen_zone_visit)
            if current_visit - t.last_seen_zone_visit > self.track_expire_visits:
                stale_ids.append(tid)
        for tid in stale_ids:
            del self.tracks[tid]

    def _check_sudden_change(self, track, current_abnormal_ratio):
        if len(track.abnormal_ratio_history) < self.min_samples_for_alert:
            return False
        baseline = sum(track.abnormal_ratio_history) / len(track.abnormal_ratio_history)
        return (current_abnormal_ratio - baseline) > self.sudden_change_threshold

    # ── 병해충 종류 판별 - 예외처리: Kindwise plant.id API에 문의 ──────────
    # ★ 공식 SDK(kindwise-api-client, PlantApi) 사용. pip install kindwise-api-client 필요.
    # ⚠️ health='all' 옵션을 반드시 줘야 disease 필드가 채워진다 (기본 identify()만
    # 호출하면 disease가 비어있음 - SDK 문서 기준).
    # ★★ 한국어 병명 변환: language="ko"를 우선 시도해서 API가 직접 한국어로
    # 응답하는지 확인하고, 안 되거나 사전에 없는 경우 DISEASE_NAME_KO 사전으로
    # 번역한다(확실한 안전장치). language="ko" 실제 지원 여부는 미검증이라,
    # 결과를 실제로 한 번 확인해보는 걸 권장한다.
    def diagnose_disease_type(self, box_bgr):
        success, encoded = cv2.imencode(".jpg", box_bgr)
        if not success:
            return "판별실패"

        try:
            from kindwise import PlantApi

            api = PlantApi(api_key=self.config["disease_api_key"])
            identification = api.identify(encoded.tobytes(), health="all", language="ko")

            suggestions = identification.result.disease.suggestions
            if not suggestions:
                return "정상(병 없음)"

            top = suggestions[0]
            # 신뢰도가 너무 낮은 추정치까지 그대로 병명으로 내보내지 않도록 임계값 적용
            min_confidence = self.config.get("disease_api_min_confidence", 0.5)
            if top.probability < min_confidence:
                return "미상(신뢰도 낮음)"

            # ★ API가 language="ko"로 이미 한국어를 줬다면 그대로 쓰고,
            # 영문 그대로 왔다면(사전 지원 안 되는 경우) 우리 사전으로 번역한다.
            disease_name_ko = translate_disease_name(top.name)

            print(f"  [Kindwise plant.id] {top.name} -> {disease_name_ko} "
                  f"신뢰도={top.probability:.1%}")
            return disease_name_ko

        except ImportError:
            print("  [경고] kindwise-api-client 미설치: pip install kindwise-api-client")
            return "판별실패"
        except (KeyError, AttributeError, IndexError) as e:
            print(f"  [경고] Kindwise 응답 파싱 실패 (스키마 변경 가능성): {e}")
            return "판별실패"
        except Exception as e:
            print(f"  [경고] Kindwise 병해충 판별 API 호출 실패: {e}")
            return "판별실패"
            return "판별실패"

    # ── 메인 인터페이스 ──
    def detect(self, frame, zone_id):
        self.zone_visit_count[zone_id] = self.zone_visit_count.get(zone_id, 0) + 1

        results = self.model(
            frame,
            conf=self.config["conf_threshold"],
            iou=self.config["iou_threshold"],
            imgsz=self.imgsz,
            verbose=False,
        )
        annotated_frame = frame
        h_frame, w_frame = frame.shape[:2]

        # ── 1단계: YOLO 박스(작물 종류만) 전부 모으기 ──
        candidates = []
        for r in results:
            annotated_frame = r.plot()

            for box in r.boxes:
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])

                crop_name = self.id_to_crop.get(class_id)
                if crop_name is None:
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0])
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w_frame, x2), min(h_frame, y2)
                box_bgr = frame[y1:y2, x1:x2]

                candidates.append({
                    "crop_name": crop_name,
                    "confidence": confidence,
                    "x1": x1, "box_bgr": box_bgr,
                })

        # ── 2단계: 같은 구역·같은 작물 안에서 좌->우 순번 할당 ──
        candidates = self._assign_slot_indices(candidates)

        # ── 3단계: 순번 기준 추적 + 색상 분석(병해충 1차 판단 포함) ──
        detections = []
        for item in candidates:
            crop_name = item["crop_name"]
            confidence = item["confidence"]
            box_bgr = item["box_bgr"]
            slot_index = item["slot_index"]

            profile = self.crop_color_profiles.get(crop_name)

            if profile is None or box_bgr.size == 0:
                detections.append(DetectionResult(
                    crop_id=crop_name, confidence=confidence,
                    ripeness_percent=None, ripeness_percent_smoothed=None,
                    is_ripe=False, disease_detected=False, box_bgr=box_bgr,
                ))
                continue

            analysis = self._analyze_fruit_color(box_bgr, profile)
            if analysis is None:
                continue

            track = self._match_or_create_track(zone_id, crop_name, slot_index)

            # ★ 1차 판단: 색상 기반 병해충 여부
            disease_detected = self._classify_disease_by_color(analysis["abnormal_ratio"], profile)
            # 보조 신호: 색상 급변 조기경보 (이력 갱신 전에 먼저 비교)
            color_change_alert = self._check_sudden_change(track, analysis["abnormal_ratio"])

            if analysis["progress"] is not None:
                track.progress_history.append(analysis["progress"])
            track.abnormal_ratio_history.append(analysis["abnormal_ratio"])

            ripeness = analysis["progress"] * 100 if analysis["progress"] is not None else None
            ripeness_smoothed = (
                (sum(track.progress_history) / len(track.progress_history)) * 100
                if len(track.progress_history) > 0 else None
            )
            is_ripe = (ripeness_smoothed is not None) and (
                ripeness_smoothed >= self.config["ripe_threshold_percent"]
            )

            detection = DetectionResult(
                crop_id=crop_name,
                confidence=confidence,
                ripeness_percent=ripeness,
                ripeness_percent_smoothed=ripeness_smoothed,
                is_ripe=is_ripe,
                disease_detected=disease_detected,
                box_bgr=box_bgr,
                track_id=track.track_id,
                color_change_alert=color_change_alert,
            )

            if disease_detected or color_change_alert:
                if disease_detected and color_change_alert:
                    detection.diagnosis_trigger = "both"
                elif disease_detected:
                    detection.diagnosis_trigger = "color"
                else:
                    detection.diagnosis_trigger = "color_change"

                detection.disease_type = self.diagnose_disease_type(box_bgr)

            detections.append(detection)

        self._prune_stale_tracks()
        return annotated_frame, detections
