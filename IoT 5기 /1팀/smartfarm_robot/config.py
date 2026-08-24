"""
config.py
프로젝트 전체에서 쓰는 설정값을 한곳에 모아둔다.

"""

import os
from pathlib import Path

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)


def find_model_path(filename="best.pt"):
    """프로젝트 전체에서 best.pt를 찾아 절대 경로를 반환한다."""
    search_roots = [CURRENT_DIR, PROJECT_ROOT]
    for root in search_roots:
        if not root:
            continue
        for path in Path(root).rglob(filename):
            if path.is_file():
                return str(path.resolve())
    return os.path.join(CURRENT_DIR, "models", filename)


CONFIG = {
    # --- 로봇 / 사용자 식별자 ---
    "user_id": "ddalgi",
    "robot_id": "R001",

    # --- YOLO 모델 (★ 4클래스: eggplant/grape/strawberry/k_melon) ---
    "model_path": find_model_path("best.pt"),
    "class_map_path": os.path.join(CURRENT_DIR, "models", "class_map.json"),
    "conf_threshold": 0.5,
    "iou_threshold": 0.7,
    # ★ True면 클래스 구분 없이 겹치는 박스는 신뢰도가 가장 높은 것만 남긴다.
    # 같은 물체가 서로 다른 두 클래스로 중복 인식되는 문제를 막기 위함.
    "agnostic_nms": True,
    # ★ 추론 해상도. 640 대비 작게/멀리 찍힌 객체 탐지력이 크게 개선됨을 실측 확인.
    #   단, 이미 화면을 꽉 채운 큰 객체는 오히려 놓칠 수 있어 트레이드오프가 있음.
    #   반드시 비동기 추론(아래 async_inference)과 함께 적용할 것.
    "imgsz": 1280,

    "vision_enabled": True,   # False면 카메라/YOLO 없이 "주행 전용 모드"로 동작
    # ★ VNC/모니터 없이(헤드리스) 돌릴 때 False로. cv2.imshow() 창을 아예 안 띄워서
    # "화면에 연결할 수 없음" 오류 없이 실행된다.
    "show_preview": True,
    # ★ 카메라 2대 사용. zone_id/batch_id는 카메라 구분 없이 공유한다
    # (MQTT로는 "구역에서 어떤 작물이 발견됐는지"만 중요하지, 어느 카메라가
    # 찍었는지는 서버/앱 쪽 관심사가 아니기 때문 - 사용자 확인 완료).
    "camera_indices": [
    "/dev/v4l/by-path/platform-xhci-hcd.1-usb-0:2:1.0-video-index0",
    "/dev/v4l/by-path/platform-xhci-hcd.0-usb-0:2:1.0-video-index0", ],
    "camera_labels": {
    "/dev/v4l/by-path/platform-xhci-hcd.1-usb-0:2:1.0-video-index0": "right",
    "/dev/v4l/by-path/platform-xhci-hcd.0-usb-0:2:1.0-video-index0": "left",
    },
    # ★ 비동기(백그라운드 스레드) 추론 사용 여부. True 권장 (하트비트 끊김 방지).
    "async_inference": True,

    # --- 캡처 저장 경로 / 주기 ---
    "capture_dir": os.path.join(CURRENT_DIR, "captures"),
    "save_detected_boxes": True,
    # ⚠️ [더 이상 사용되지 않음] 캡처는 이제 타이머가 아니라 아두이노의
    # 마커 정지(STATUS=PAUSED) 감지로 트리거된다 (main_controller.py 참고).
    # 이 값은 코드 어디서도 안 읽지만, 과거 설정과의 호환을 위해 남겨둠.
    "capture_interval_sec": 5,

    # --- 익음 판정 임계값 ---
    "ripe_threshold_percent": 75,
    "sample_size": 35,

    # --- 시간에 따른 색상 변화 추적 (병해충 조기경보 "보조" 신호) ---
    "color_tracking": {
        "history_window": 5,
        "sudden_change_abnormal_ratio_delta": 0.15,
        "min_samples_for_alert": 2,
        "track_expire_visits": 3,
    },

    # --- MQTT (앱/서버 <-> 라즈베리파이 통신) ---
    # ★ AWS 배포: MQTT/HTTP 전부 AWS 서버 IP를 통해 이뤄진다. 실제 인스턴스
    #   준비되면 아래 두 값만 교체하면 된다.
    "mqtt_broker": "AWS 서버 IP 또는 도메인",  # ex) "
    "mqtt_port": 1883,                 # ★ 공인 인터넷 구간 -> TLS 기본 포트 권장 (평문 1883 지양)
    "mqtt_client_id": "smartfarm-cam-01",
    "mqtt_use_auth": False,
    "mqtt_username": "TODO",
    "mqtt_password": "TODO",
    "mqtt_use_tls": False,
    "mqtt_ca_cert": "./certs/ca.crt",

    # 문서 3-1: 로봇 상태 보고 (고정 토픽, payload에 robot_id 포함)
    "telemetry_topic_template": "ddalgi/robot/status",
    # 문서 3-4: 순찰/이동 명령 (앱 -> 서버 -> 로봇). "command" 키 사용, /move 접미사 없음.
    "move_command_topic_template": "ddalgi/robot/command/{robot_id}",
    # ★ 작물 메타데이터(이미지 제외) 발행 토픽. HTTP 엔드포인트 경로와 동일 문자열 사용.
    "crop_meta_topic_template": "api/upload/crop",
    # 문서 3-3: 온습도 센서 보고 토픽.
    "env_topic_template": "ddalgi/sensor/env",
    # 문서 4-1: 서버 -> 앱 질병 경고 (로봇은 구독/발행하지 않음, 참고용으로만 보관)
    "disease_alert_topic_template": "ddalgi/alert/disease/{user_id}",

    # --- 아두이노 USB 직결 연결 ---
    "arduino_port": "/dev/ttyUSB0",
    "arduino_baud": 115200,
    "arduino_reconnect_interval_sec": 5,
    "heartbeat_interval_sec": 1,
    "telemetry_poll_interval_sec": 0.3,
    "telemetry_republish_interval_sec": 3,
    # ★ 온습도 센서 보고 주기 (변화가 느린 값이라 텔레메트리보다 여유있게)
    "env_report_interval_sec": 20,
    "env_sensor_gpio_pin": "D4", #board.D4 = BCM GPIO4. real pin = data pin
    "env_sensor_type": "DHT11",  #"DHT11" or "DHT22"

    # ══════════════════════════════════════════════════════════════════
    # ▼▼▼ [PAUSE-BEFORE-CAPTURE 기능] 이 블록을 지우면 기능이 꺼집니다 ▼▼▼
    # ══════════════════════════════════════════════════════════════════
    "capture_pause_stabilize_sec": 1.5,
    # ══════════════════════════════════════════════════════════════════
    # ▲▲▲ [PAUSE-BEFORE-CAPTURE 기능] 끝 ▲▲▲
    # ══════════════════════════════════════════════════════════════════

    # ★★★ [zone_id 체계 변경] 마커별로 구역을 나누던 방식을 폐지했다.
    # zone_id는 이제 "a1" 하나로 완전히 고정된다 (그 외 다른 구역 없음).
    # 마커는 더 이상 "구역 구분"이 아니라 "멈춰서 사진을 찍는 위치(트리거 지점)"로
    # 역할이 재정의됐다 - 즉 몇 번째 마커인지와 무관하게 항상 같은 zone_id로 보고된다.
    "fixed_zone_id": "a1",

    # --- 서버 REST API (S3 업로드 + DB 로깅, 이미지 전용) ---
    "http_upload_url": "http://AWS_서버_IP:12345/api/upload/crop",

    # --- 병해충 종류 판별 API (Kindwise plant.id로 확정) ---
    # 가입: https://admin.kindwise.com (무료 테스트 크레딧 제공)
    # 설치: pip install kindwise-api-client
    # 참고: https://plant.id/docs
    # ✅ 최종 확정 (2026-08-14): plant.id 연동 실측 검증 완료, 아래 키만 실제
    # 발급받은 값으로 교체하면 바로 사용 가능.
    "disease_api_url": "https://plant.id/docs",  # 참고용 (SDK 사용 시 미사용)
    "disease_api_key": "API_KEY",  # ← 실제 발급받은 plant.id 키로 교체
    # 이 값보다 낮은 확신도의 병명은 "미상"으로 처리한다.
    "disease_api_min_confidence": 0.5,
}

# ── 작물별 색상 프로필 ──
# ★ disease_threshold 부활: 4클래스 전환으로 YOLO가 더 이상 병해충을 분류하지
#   않으므로, "이번 캡처의 이상색상비율(abnormal_ratio)"이 이 값을 넘으면
#   1차적으로 병해충으로 판단한다. color_change_alert(시간 추이 비교)는
#   별도의 보조 신호로 계속 동작한다.
#   ※ 실측 보정 전 임시값. calibrate_color_profiles.py로 재보정 권장.
CROP_COLOR_PROFILES = {
    "eggplant": {
        "hue_start": 45, "hue_end": 150, "direction": 1,
        "margin": 0.15, "min_saturation": 12,
        "disease_threshold": 0.70,
    },
    "grape": {
        "hue_start": 50, "hue_end": 0, "direction": -1,
        "margin": 0.15, "min_saturation": 50,
        "disease_threshold": 0.20,
    },
    "strawberry": {
        "hue_start": 60, "hue_end": 0, "direction": -1,
        "margin": 0.15, "min_saturation": 60,
        "disease_threshold": 0.65,
    },
    "oriental_melon": {
        "hue_start": 65, "hue_end": 25, "direction": -1,
        "margin": 0.15, "min_saturation": 50,
        "disease_threshold": 0.70,
    },
}


def resolve_topics(cfg):
    """robot_id/user_id를 반영해 실제 토픽 문자열을 만들어 cfg에 채워 넣는다."""
    cfg["telemetry_topic"] = cfg["telemetry_topic_template"].format(robot_id=cfg["robot_id"])
    cfg["move_command_topic"] = cfg["move_command_topic_template"].format(robot_id=cfg["robot_id"])
    cfg["crop_meta_topic"] = cfg["crop_meta_topic_template"]
    cfg["env_topic"] = cfg["env_topic_template"]
    cfg["disease_alert_topic"] = cfg["disease_alert_topic_template"].format(user_id=cfg["user_id"])
    return cfg


def zone_count_to_name(cfg, zone_count=None):
    """
    ★ [zone_id 체계 변경] 더 이상 마커 카운트로 구역을 나누지 않는다.
    zone_count 인자는 (기존 호출부와의 호환을 위해) 받기만 하고 실제로는
    쓰지 않으며, 항상 config의 fixed_zone_id("a1")를 반환한다.
    """
    return cfg.get("fixed_zone_id", "a1")
