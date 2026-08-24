"""카메라 스트리밍 + 인식 파이프라인 모듈

이 모듈이 실제로 카메라를 열고, 실시간 스트림용 프레임을 만들고,
QR/의류 인식 결과를 화면에 겹쳐 그리고, 두 개가 동시에 인식되면 사진을
저장하는 전체 흐름을 담당한다. 백그라운드 스레드 2개로 동작한다.

- camera_loop: 카메라에서 프레임을 계속 읽어와 스트리밍용 최신 프레임
  (latest_frame)을 갱신한다. /video_feed가 읽어가는 값이 바로 이것이다.
- detection_loop: QR 인식과 의류(상의) 인식을 순서대로 반복 실행해서
  최신 결과(latest_qr_codes, latest_clothing_boxes)를 갱신한다.

왜 두 스레드로 나눴는가: QR/의류 인식은 YOLO 추론이라 한 번에 1~2초씩
걸린다. camera_loop 안에서 그대로 실행하면 그 시간만큼 스트리밍이
멈춰버린다. 그래서 인식은 별도 스레드에서 "가장 최근 프레임 기준으로"
계속 돌게 하고, camera_loop는 인식 스레드가 마지막으로 계산해 둔 결과를
그때그때 가져다 그리기만 한다. 또한 QR/의류 인식 두 개를 각자 스레드로
나눠 동시에 돌렸더니 이 라즈베리파이(4코어)의 CPU를 인식 스레드 둘이서
다 써버려 스트리밍이 느려지는 문제가 있었다 -- 그래서 지금은 인식
스레드 하나 안에서 QR → 의류 순서로 이어서 실행한다(torch 스레드 수도
1개로 제한해 추가로 CPU를 아낀다. config.py 참고).
"""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from clothing_detector import detect_clothing_yolo, draw_clothing_overlay
from config import (
    CAMERA_DEVICE,
    CAMERA_INDEX,
    IMAGE_DIR,
    MAX_CAMERA_INDEX,
    SNAPSHOT_COOLDOWN_SECONDS,
    STREAM_FRAME_DELAY_SECONDS,
    STREAM_FRAME_HEIGHT,
    STREAM_FRAME_WIDTH,
    STREAM_TARGET_FPS,
)
from database import get_connection, upsert_image_record
from gemini_service import analyze_image_with_gemini
from qr_detector import detect_qr_codes, detect_qr_id, draw_qr_overlay

# ---- 스트리밍용 최신 프레임 (여러 클라이언트가 동시에 /video_feed를
#      열어도 각자 이 값을 복사해서 읽어가므로 락으로 보호한다) ----
frame_lock = threading.Lock()
latest_frame: Any = None

# ---- 스냅샷(자동 저장) 관련 상태 ----
last_snapshot_time = 0.0
last_uploaded_image_id: int | None = None

# ---- 카메라 스레드 시작 여부 (앱이 여러 번 startup 이벤트를 받아도
#      스레드가 중복 실행되지 않도록 막는 가드) ----
camera_thread_started = False
camera_lock = threading.Lock()

# ---- detection_loop에 "지금 인식할 프레임"을 전달하는 슬롯 ----
detection_input_lock = threading.Lock()
detection_input_frame: Any = None

# ---- detection_loop가 계산한 최신 인식 결과 ----
qr_result_lock = threading.Lock()
latest_qr_codes: list[tuple[tuple[int, int, int, int], str]] = []
clothing_result_lock = threading.Lock()
latest_clothing_boxes: list[tuple[int, int, int, int]] = []

# ---- 웹 UI에서 조절하는 밝기 보정값(-100~100) ----
brightness_lock = threading.Lock()
stream_brightness = 0


def open_camera_source(source: int | str) -> cv2.VideoCapture:
    return cv2.VideoCapture(str(source))


def configure_camera_stream(capture: cv2.VideoCapture) -> None:
    capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, STREAM_FRAME_WIDTH)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, STREAM_FRAME_HEIGHT)
    capture.set(cv2.CAP_PROP_FPS, STREAM_TARGET_FPS)


def find_available_camera_source() -> str | int:
    """설정된 장치 경로/인덱스 중 실제로 열리는 카메라를 찾는다."""
    seen = set()
    candidates: list[str | int] = []
    if CAMERA_DEVICE:
        candidates.append(CAMERA_DEVICE)
    candidates.extend([CAMERA_INDEX] + list(range(MAX_CAMERA_INDEX + 1)))

    for source in candidates:
        if source in seen:
            continue
        seen.add(source)
        capture = None
        try:
            capture = open_camera_source(source)
            if capture.isOpened():
                capture.release()
                return source
        except Exception:
            pass
        finally:
            if capture is not None:
                capture.release()

    return CAMERA_DEVICE if CAMERA_DEVICE else CAMERA_INDEX


def create_placeholder_frame(message: str = "Camera unavailable") -> np.ndarray:
    """카메라를 못 열었을 때 스트림에 대신 내보낼 안내 화면."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[:, :] = (18, 24, 32)
    cv2.putText(
        frame,
        message,
        (40, 240),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    return frame


def apply_stream_brightness(frame: Any) -> Any:
    with brightness_lock:
        brightness = stream_brightness
    if brightness == 0 or frame is None:
        return frame
    return cv2.convertScaleAbs(frame, alpha=1.0, beta=brightness)


# ---- 스냅샷 저장 ----

def remove_existing_file(file_path: str) -> None:
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass


def save_frame_to_disk(frame: Any, image_path: Path) -> None:
    try:
        success = cv2.imwrite(str(image_path), frame)
        if not success:
            raise RuntimeError("Failed to write frame to disk")
    except Exception:
        raise


def handle_snapshot(frame: Any, qr_id: int) -> None:
    """QR+상의가 동시에 인식됐을 때: 사진을 저장하고 Gemini 설명을 붙여 DB에 기록한다.

    Gemini 호출(네트워크, 수 초 소요)이 포함되어 있어 process_detected_frame이
    이 함수를 직접 부르지 않고 항상 별도 스레드에서 실행한다.
    """
    image_name = f"qr_{qr_id}.jpg"
    image_path = IMAGE_DIR / image_name

    try:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT filepath FROM images WHERE id = ?",
                (qr_id,),
            ).fetchone()

        if row and row["filepath"]:
            remove_existing_file(row["filepath"])
    except Exception:
        pass

    try:
        save_frame_to_disk(frame, image_path)
    except Exception:
        return

    description = analyze_image_with_gemini(image_path) or ""

    try:
        upsert_image_record(qr_id, str(image_path), description)
    except Exception:
        pass


def process_detected_frame(
    frame: Any,
    clothing_boxes: list[tuple[int, int, int, int]] | None = None,
    qr_codes: list[tuple[tuple[int, int, int, int], str]] | None = None,
) -> None:
    """상의+QR이 동시에, 그리고 조건을 만족할 때만 스냅샷 저장을 트리거한다.

    트리거 조건:
    1) 상의가 인식되고, QR이 1~10 슬롯 번호로 해석될 것
    2) 마지막으로 저장한 슬롯 번호와 다를 것 (같은 옷을 계속 비춰도 중복 저장 안 함)
    3) 마지막 저장 이후 SNAPSHOT_COOLDOWN_SECONDS(3초)가 지났을 것
    """
    global last_snapshot_time, last_uploaded_image_id

    if frame is None:
        return

    clothing_detected = bool(clothing_boxes if clothing_boxes is not None else detect_clothing_yolo(frame))
    numeric_id = detect_qr_id(qr_codes if qr_codes is not None else detect_qr_codes(frame))
    if not clothing_detected or numeric_id is None:
        return
    if numeric_id == last_uploaded_image_id:
        # 직전에 저장한 것과 같은 ID면, 다른 ID가 한 번이라도 저장된
        # 뒤에야 다시 저장을 허용한다.
        return
    try:
        current_time = time.time()
        if current_time - last_snapshot_time < SNAPSHOT_COOLDOWN_SECONDS:
            return
    except Exception:
        return
    try:
        last_snapshot_time = time.time()
        last_uploaded_image_id = numeric_id
        # handle_snapshot은 Gemini 네트워크 호출(수 초)과 디스크 저장을
        # 포함한다. 여기서 바로 실행하면 camera_loop의 프레임 캡처가 그
        # 시간만큼 멈춰 스트림이 끊긴다. 별도 스레드로 넘긴다 --
        # last_snapshot_time은 이미 위에서 갱신했으므로, 이 스레드가
        # 실행되는 도중에도 다음 프레임의 쿨다운 검사는 정상 동작한다.
        threading.Thread(target=handle_snapshot, args=(frame.copy(), numeric_id), daemon=True).start()
    except Exception:
        pass


# ---- 백그라운드 스레드 ----

def camera_loop() -> None:
    """카메라에서 프레임을 계속 읽어 스트리밍용 최신 프레임을 갱신하는 루프."""
    while True:
        capture = None
        camera_source = None
        try:
            camera_source = find_available_camera_source()
            capture = open_camera_source(camera_source)
            if not capture.isOpened():
                raise RuntimeError(f"Camera unavailable: {camera_source}")

            configure_camera_stream(capture)

            while True:
                try:
                    success, frame = capture.read()
                    if not success or frame is None:
                        raise RuntimeError("No frame read from camera")

                    frame = apply_stream_brightness(frame)
                    # 상의(파란색)와 QR(빨간색)은 공유 백그라운드 스레드
                    # (detection_loop)에서 인식한다 -- YOLO 추론이 느려서
                    # 이 루프 안에서 직접 돌리면 스트림이 멈춘다.
                    with detection_input_lock:
                        global detection_input_frame
                        detection_input_frame = frame.copy()

                    with clothing_result_lock:
                        clothing_boxes = latest_clothing_boxes
                    overlay_frame = draw_clothing_overlay(frame, clothing_boxes)

                    with qr_result_lock:
                        qr_codes = latest_qr_codes
                    overlay_frame = draw_qr_overlay(overlay_frame, qr_codes)

                    with frame_lock:
                        global latest_frame
                        latest_frame = overlay_frame.copy()

                    try:
                        process_detected_frame(frame, clothing_boxes, qr_codes)
                    except Exception:
                        pass

                    time.sleep(STREAM_FRAME_DELAY_SECONDS)
                except Exception:
                    with frame_lock:
                        latest_frame = create_placeholder_frame(
                            f"Camera unavailable: {camera_source}"
                        )
                    time.sleep(0.5)
        except Exception:
            with frame_lock:
                latest_frame = create_placeholder_frame(
                    f"Camera unavailable: {camera_source or CAMERA_DEVICE}"
                )
            time.sleep(1.0)
        finally:
            try:
                if capture is not None:
                    capture.release()
            except Exception:
                pass


def detection_loop() -> None:
    """가장 최근 프레임에 대해 QR 인식 → 의류 인식을 순서대로 반복하는 루프."""
    global latest_qr_codes, latest_clothing_boxes

    while True:
        with detection_input_lock:
            frame = detection_input_frame

        if frame is None:
            time.sleep(0.1)
            continue

        codes = detect_qr_codes(frame)
        with qr_result_lock:
            latest_qr_codes = codes

        boxes = detect_clothing_yolo(frame)
        with clothing_result_lock:
            latest_clothing_boxes = boxes


def start_camera_thread_once() -> None:
    """camera_loop / detection_loop 스레드를 (한 번만) 시작한다."""
    global camera_thread_started

    with camera_lock:
        if camera_thread_started:
            return
        camera_thread_started = True

        threading.Thread(target=camera_loop, daemon=True).start()
        threading.Thread(target=detection_loop, daemon=True).start()
