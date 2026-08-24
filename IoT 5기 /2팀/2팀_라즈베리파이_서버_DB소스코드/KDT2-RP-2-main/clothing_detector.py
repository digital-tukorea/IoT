"""의류(상의) 인식 모듈

DeepFashion2 데이터셋으로 학습된 YOLOv8 세그멘테이션 모델로 카메라
프레임에서 "입고 있는 상의"를 찾는다. DeepFashion2는 13개 의류
클래스(상의/하의/원피스 등)를 구분하는데, 그중 상의류 클래스만 남기고
바지·치마·원피스는 걸러낸다. QR 인식과 마찬가지로 추론이 무거워서
(약 2초) camera_stream.detection_loop의 백그라운드 스레드에서만 호출된다.
"""

from __future__ import annotations

from typing import Any

import cv2

from config import CLOTHING_MODEL_PATH

try:
    from ultralytics import YOLO
except Exception:
    YOLO = None

try:
    clothing_model = YOLO(str(CLOTHING_MODEL_PATH)) if YOLO is not None and CLOTHING_MODEL_PATH.exists() else None
except Exception:
    clothing_model = None

# DeepFashion2 클래스 인덱스 중 "상의"에 해당하는 것만 모음
# (짧은/긴팔 셔츠, 짧은/긴팔 아우터, 조끼, 슬링) -- 하의·원피스류는 제외
TOP_CLASS_IDS = {0, 1, 2, 3, 4, 5}


def detect_clothing_yolo(frame: Any) -> list[tuple[int, int, int, int]]:
    """BGR 프레임에서 상의를 찾아 바운딩박스 목록으로 반환한다."""
    results: list[tuple[int, int, int, int]] = []
    if clothing_model is None or frame is None:
        return results

    try:
        predictions = clothing_model.predict(frame, verbose=False)
        if not predictions:
            return results

        for box in predictions[0].boxes:
            class_id = int(box.cls[0])
            if class_id not in TOP_CLASS_IDS:
                continue
            x1, y1, x2, y2 = box.xyxy[0]
            results.append((int(x1), int(y1), int(x2), int(y2)))
    except Exception:
        pass

    return results


def draw_clothing_overlay(frame: Any, boxes: list[tuple[int, int, int, int]]) -> Any:
    """탐지된 상의 주변에 파란색 테두리를 그려 넣는다."""
    if frame is None or not boxes:
        return frame

    overlay = frame.copy()
    for (x1, y1, x2, y2) in boxes:
        cv2.rectangle(overlay, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 3)
        cv2.putText(overlay, "CLOTHING", (int(x1), max(15, int(y1) - 10)),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2, cv2.LINE_AA)
    return overlay
