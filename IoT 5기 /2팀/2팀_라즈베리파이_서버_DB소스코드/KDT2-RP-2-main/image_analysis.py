"""저장된 옷 사진 분석 모듈

옷장에 이미 저장된 사진 한 장을 분석해서 (1) 일반 COCO YOLO 라벨 목록과
(2) 사람이 읽을 수 있는 요약 문장을 만들어낸다. 여기서 쓰는 yolo_model은
범용 COCO 사전학습 모델로, 상의만 찾는 clothing_detector.py의 DeepFashion2
모델과는 별개다(이 모듈은 "사진에 뭐가 찍혀 있나" 정도의 보조 라벨링 용도).

local_image_summary()는 Gemini를 쓸 수 없을 때만 쓰는 로컬 대체 요약이며,
DB의 description 컬럼에는 절대 쓰이지 않는다(그건 gemini_service의 몫).
여기서는 /api/recommend/analyze 응답의 일회성 요약(summary) 필드에만
쓰인다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2

from config import logger

try:
    from ultralytics import YOLO
except Exception:
    YOLO = None

try:
    yolo_model = YOLO("yolov8n.pt") if YOLO is not None else None
except Exception:
    yolo_model = None


def resolve_class_name(model: Any, class_id: int) -> str:
    """YOLO 모델의 클래스 인덱스를 사람이 읽을 수 있는 이름으로 바꾼다."""
    try:
        names = getattr(model, "names", {})
        if isinstance(names, dict):
            return str(names.get(class_id, "")).lower()
        if isinstance(names, list) and class_id < len(names):
            return str(names[class_id]).lower()
    except Exception:
        pass
    return ""


def analyze_image_labels(image_path: Path) -> list[str]:
    """저장된 사진 하나에서 COCO 라벨 목록(예: person, tie)을 뽑아낸다."""
    if yolo_model is None:
        return []

    try:
        frame = cv2.imread(str(image_path))
        if frame is None:
            return []

        results = yolo_model.predict(frame, verbose=False)
        if not results:
            return []

        labels: set[str] = set()
        for box in results[0].boxes:
            try:
                class_id = int(box.cls[0])
                class_name = resolve_class_name(yolo_model, class_id)
                if class_name:
                    labels.add(class_name)
            except Exception:
                continue

        return sorted(labels)
    except Exception:
        return []


def get_image_color_name(image_path: Path) -> str:
    """이미지의 평균 색상을 대략적인 색 이름으로 분류한다(로컬 요약용)."""
    try:
        frame = cv2.imread(str(image_path))
        if frame is None:
            return "neutral"

        average_bgr = frame.mean(axis=(0, 1))
        blue, green, red = [float(c) for c in average_bgr]
        if red >= green and red >= blue:
            if red - max(green, blue) > 50:
                return "red"
            return "warm"
        if green >= red and green >= blue:
            if green - max(red, blue) > 50:
                return "green"
            return "olive"
        if blue >= red and blue >= green:
            if blue - max(red, green) > 50:
                return "blue"
            return "cool"
        return "neutral"
    except Exception:
        return "neutral"


def local_image_summary(image_path: Path) -> str:
    """Gemini 없이 색상+라벨만으로 만드는 간단한 대체 요약 문장."""
    core_color = get_image_color_name(image_path)
    labels = analyze_image_labels(image_path)
    label_text = ", ".join(labels[:2]) if labels else "옷"
    if core_color in {"red", "blue", "green"}:
        return f"{core_color} 톤의 {label_text}으로 보여요. 편안하게 입기 좋습니다."
    if core_color in {"warm", "cool", "olive"}:
        return f"은은한 {core_color} 컬러의 {label_text}으로 일상에 잘 어울립니다."
    return f"기본적인 {label_text}으로 보이며, 스타일링하기 좋습니다."


def build_inventory_analysis(inventory: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """/api/recommend/analyze 용으로 인벤토리 각 항목의 라벨+요약을 만든다."""
    analysis = []
    for item in inventory:
        try:
            image_path = Path(str(item.get("filepath", "")))
            if not image_path.exists():
                logger.warning("Inventory image path does not exist: %s", image_path)
                continue

            labels = analyze_image_labels(image_path)
            # 촬영 시점에 Gemini가 이미 만들어 DB에 저장해 둔 description을
            # 재사용한다(handle_snapshot 참고). 요청마다 Gemini를 다시
            # 호출하면 인벤토리가 10개일 때 응답이 느려져 클라이언트
            # 타임아웃이 났던 적이 있어, 저장된 값이 없을 때만 로컬 요약으로
            # 대체한다.
            summary = item.get("description") or local_image_summary(image_path)
            analysis.append(
                {
                    "id": item.get("id"),
                    "filepath": item.get("filepath"),
                    "description": item.get("description", ""),
                    "yolo_labels": labels,
                    "summary": summary,
                }
            )
        except Exception as exc:
            logger.warning("Failed analysis for inventory item %s: %s", item.get("id"), exc)
            continue
    return analysis
