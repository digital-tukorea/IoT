"""MQTT 모듈

물리 레일 장치에 "이 옷을 가져와라"라고 알려주는 MQTT 발행을 담당한다.
브로커는 이 기기에서 함께 도는 mosquitto를 사용한다(기본 127.0.0.1:1883).
paho-mqtt 라이브러리가 없거나 브로커 연결에 실패해도 서버 자체는 계속
동작해야 하므로, 실패 시 예외를 올리지 않고 False만 반환한다.
"""

from __future__ import annotations

import json
import threading
import time
from typing import Any

from config import MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_TOPIC

try:
    from paho.mqtt import client as mqtt
except Exception:
    mqtt = None

mqtt_client: Any = None
mqtt_client_lock = threading.Lock()


def initialize_mqtt() -> None:
    """MQTT 브로커에 연결한다. 앱 시작 시 한 번 호출된다."""
    global mqtt_client
    if mqtt is None or mqtt_client is not None:
        return

    try:
        mqtt_client = mqtt.Client(client_id="smart_closet_backend", clean_session=True)
        mqtt_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 10)
        mqtt_client.loop_start()
    except Exception:
        mqtt_client = None


def publish_slot_id(image_id: int) -> bool:
    """레일 제어 토픽(rail/target_qr)으로 슬롯 번호를 발행한다.

    /api/recommend가 추천 3벌을 고른 뒤와 /api/send_id/{id}에서 사용된다.
    """
    global mqtt_client
    if mqtt is None:
        return False

    if mqtt_client is None:
        initialize_mqtt()

    if mqtt_client is None:
        return False

    try:
        payload = json.dumps(
            {
                "slot_id": image_id,
                "device_id": "smart_closet_backend",
                "ts": int(time.time()),
            },
            ensure_ascii=False,
        )
        result = mqtt_client.publish(MQTT_TOPIC, payload, qos=1, retain=False)
        return getattr(result, "rc", None) == mqtt.MQTT_ERR_SUCCESS
    except Exception:
        return False
