"""QR 인식 모듈

YOLOv8 기반 QR 탐지기(qrdet/qreader)로 카메라 프레임에서 QR 코드를
찾아 위치와 디코딩된 텍스트를 반환한다. 각도가 틀어졌거나 옷 태그처럼
어수선한 배경 속에 있는 작은 QR도 놓치지 않으려고, 전체 프레임을 한 번에
스캔하는 방식(ZBar 등) 대신 객체 탐지 방식을 쓴다. 대신 추론이 무거워서
(이 기기 CPU에서 약 1~2초) camera_stream.detection_loop의 백그라운드
스레드에서만 호출된다.
"""

from __future__ import annotations

from typing import Any

import cv2

from config import VALID_QR_IDS

try:
    from qreader import QReader
except Exception:
    QReader = None

try:
    qr_reader = QReader() if QReader is not None else None
except Exception:
    qr_reader = None


def detect_qr_codes(frame: Any) -> list[tuple[tuple[int, int, int, int], str]]:
    """BGR 프레임에서 QR 코드를 찾아 [(바운딩박스, 디코딩된 텍스트), ...] 로 반환한다."""
    results: list[tuple[tuple[int, int, int, int], str]] = []
    if qr_reader is None or frame is None:
        return results

    try:
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        texts, detections = qr_reader.detect_and_decode(image=rgb_frame, return_detections=True)
        for text, detection in zip(texts, detections):
            x1, y1, x2, y2 = detection["bbox_xyxy"]
            results.append(((int(x1), int(y1), int(x2), int(y2)), (text or "").strip()))
    except Exception:
        pass

    return results


def draw_qr_overlay(frame: Any, qr_codes: list[tuple[tuple[int, int, int, int], str]]) -> Any:
    """탐지된 QR 코드 주변에 빨간색 테두리와 디코딩된 값을 그려 넣는다."""
    if frame is None or not qr_codes:
        return frame

    overlay = frame.copy()
    for (x1, y1, x2, y2), text in qr_codes:
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 0, 255), 3)
        label = f"QR {text}" if text else "QR"
        cv2.putText(overlay, label, (x1, max(15, y1 - 10)),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2, cv2.LINE_AA)
    return overlay


def parse_valid_qr_id(raw_value: str) -> int | None:
    """디코딩된 QR 텍스트를 1~10 사이의 옷장 슬롯 번호로 해석한다. 범위 밖이면 None."""
    try:
        value = int(str(raw_value).strip())
        if value in VALID_QR_IDS:
            return value
    except Exception:
        return None
    return None


def detect_qr_id(qr_codes: list[tuple[tuple[int, int, int, int], str]]) -> int | None:
    """탐지된 QR 목록 중 유효한 슬롯 번호(1~10)로 해석되는 첫 값을 반환한다."""
    for _box, text in qr_codes:
        numeric_id = parse_valid_qr_id(text)
        if numeric_id is not None:
            return numeric_id
    return None
