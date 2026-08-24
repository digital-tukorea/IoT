"""
mqtt_module.py
MQTT 연결/발행/구독을 캡슐화한다.

다른 모듈은 이 모듈이 "MQTT"라는 것을 쓴다는 사실만 알면 되고,
paho-mqtt API를 직접 다루지 않는다.

핵심 인터페이스:
  - publish(topic, payload_dict)         : 데이터 발행
  - on_command(topic, handler)           : 특정 토픽에 콜백 등록 (토픽별 라우팅)
"""

import json
import paho.mqtt.client as mqtt


class MQTTModule:
    def __init__(self, config):
        self.config = config
        self._handlers = {}  # topic(str) -> handler(dict) 함수 매핑
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=config["mqtt_client_id"],
        )

        if config["mqtt_use_auth"]:
            self.client.username_pw_set(config["mqtt_username"], config["mqtt_password"])
        if config["mqtt_use_tls"]:
            self.client.tls_set(ca_certs=config["mqtt_ca_cert"])

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    # ── 연결 ──────────────────────────────────────────────
    def connect(self):
        try:
            self.client.reconnect_delay_set(min_delay=1, max_delay=30)
            self.client.connect_async(self.config["mqtt_broker"], self.config["mqtt_port"], keepalive=60)
            self.client.loop_start()
            print(f"  [MQTT] 연결 시도 시작 (백그라운드) -> {self.config['mqtt_broker']}:{self.config['mqtt_port']}")
        except Exception as e:
            print(f"⚠️ [MQTT] 연결 초기화 중 오류: {e} (브로커 없이도 나머지 기능은 계속 동작합니다)")

    def disconnect(self):
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except Exception as e:
            print(f"  [MQTT] 종료 중 경고 (무시 가능): {e}")

    # ── 발행 ──────────────────────────────────────────────
    def publish(self, topic, payload_dict, qos=1):
        message = json.dumps(payload_dict, ensure_ascii=False)
        result = self.client.publish(topic, message, qos=qos)
        status = result[0]
        if status == 0:
            print(f"  [MQTT 발행 완료] topic={topic}")
        else:
            print(f"  [MQTT 발행 실패] topic={topic} status={status}")
        return status == 0

    # ── 명령 구독 등록 (⭐ 토픽별 라우팅의 핵심) ──────────────
    def on_command(self, topic, handler):
        """
        다른 모듈이 자기가 관심있는 토픽과 핸들러 함수를 등록한다.
        handler는 dict 하나를 인자로 받는 함수여야 한다: handler(payload: dict)
        """
        self._handlers[topic] = handler
        self.client.subscribe(topic)
        print(f"  [MQTT] 명령 채널 구독 등록: {topic}")

    # ── 내부 콜백 ─────────────────────────────────────────
    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            print(f"✅ [MQTT] 브로커 연결 성공! ({self.config['mqtt_broker']}:{self.config['mqtt_port']})")
            # 재연결 시에도 등록된 토픽을 전부 다시 구독
            for topic in self._handlers:
                client.subscribe(topic)
        else:
            print(f"❌ [MQTT] 연결 실패! 상태 코드: {reason_code}")

    def _on_message(self, client, userdata, msg):
        handler = self._handlers.get(msg.topic)
        if handler is None:
            print(f"  [MQTT 경고] 핸들러가 없는 토픽 수신: {msg.topic}")
            return
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except json.JSONDecodeError:
            print(f"  [MQTT 경고] JSON 파싱 실패, 원문: {msg.payload!r}")
            return

        try:
            handler(payload)  # ⭐ 등록된 모듈의 핸들러로 그대로 전달
        except Exception as e:
            print(f"  [MQTT 경고] 핸들러 실행 중 오류: {e}")
