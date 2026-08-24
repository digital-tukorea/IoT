"""설정 모듈

환경 변수, 경로, 스트리밍/카메라 파라미터 등 프로젝트 전역에서 쓰이는
상수들을 한곳에 모아둔다. 다른 모듈들은 대부분 이 모듈을 가장 먼저
불러오므로, 프로세스 전체에 한 번만 적용하면 되는 초기화(로깅 설정,
PyTorch 스레드 수 제한 등)도 여기서 함께 처리한다.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path


def parse_int(value: str, default: int) -> int:
    """문자열을 정수로 변환하고, 실패하면 기본값을 반환한다."""
    try:
        return int(str(value).strip())
    except Exception:
        return default


# ---- 경로 ----
BASE_DIR = Path(__file__).resolve().parent
IMAGE_DIR = BASE_DIR / "saved_images"
DATABASE_PATH = BASE_DIR / "local_gallery.db"
CLOTHING_MODEL_PATH = BASE_DIR / "models" / "deepfashion2_yolov8s-seg.pt"

IMAGE_DIR.mkdir(parents=True, exist_ok=True)

# ---- QR / 스냅샷 업로드 ----
VALID_QR_IDS = set(range(1, 11))  # 옷장 슬롯은 1~10번만 유효
SNAPSHOT_COOLDOWN_SECONDS = 3.0  # 같은 조건으로 연속 업로드되는 것을 막는 최소 간격

# ---- MQTT (레일 제어 브로커) ----
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "127.0.0.1").strip()
MQTT_BROKER_PORT = parse_int(os.getenv("MQTT_BROKER_PORT", "1883"), 1883)
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "rail/target_qr").strip()

# ---- 카메라 장치 ----
CAMERA_DEVICE = os.getenv("CAMERA_DEVICE", "/dev/video0").strip()
CAMERA_INDEX = parse_int(os.getenv("CAMERA_INDEX", "0"), 0)
MAX_CAMERA_INDEX = parse_int(os.getenv("MAX_CAMERA_INDEX", "5"), 5)

# ---- 스트리밍 파라미터 ----
STREAM_FRAME_WIDTH = parse_int(os.getenv("STREAM_WIDTH", "1280"), 1280)
STREAM_FRAME_HEIGHT = parse_int(os.getenv("STREAM_HEIGHT", "720"), 720)
STREAM_TARGET_FPS = parse_int(os.getenv("STREAM_FPS", "30"), 30)
STREAM_JPEG_QUALITY = parse_int(os.getenv("STREAM_JPEG_QUALITY", "92"), 92)
STREAM_FRAME_DELAY_SECONDS = 1 / 25  # /video_feed가 프레임을 내보내는 최대 주기(목표 상한 25fps)

# ---- Gemini API 키를 GOOGLE_API_KEY로도 노출 (google-genai SDK 호환용) ----
_api_key = os.getenv("GEMINI_API_KEY", "").strip()
if _api_key:
    os.environ.setdefault("GOOGLE_API_KEY", _api_key)

# ---- 로깅 ----
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smart_closet_backend")

# ---- PyTorch 스레드 수 제한 ----
# YOLO 추론 하나가 기본적으로 CPU 코어를 모두 쓰려고 해서, 이 라즈베리파이
# (4코어)에서 QR 인식과 의류 인식이 동시에 돌면 카메라 스트리밍용 CPU가
# 부족해져 스트림이 끊기는 문제가 있었다. 추론 1건당 코어 1개로 제한해서
# 스트리밍 루프가 CPU를 확보할 수 있게 한다. 다른 모델(QReader, YOLO 등)을
# 불러오기 전에 반드시 먼저 실행되어야 하므로 config 모듈 맨 아래(다른
# 모든 모듈이 가장 먼저 import하는 지점)에 둔다.
try:
    import torch

    torch.set_num_threads(1)
except Exception:
    pass
