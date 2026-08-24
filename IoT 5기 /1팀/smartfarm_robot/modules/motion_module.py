"""
motion_module.py
아두이노와 USB 케이블로 직접 연결해서 이동 명령을 전달하고,
아두이노가 주기적으로 보내는 배터리/센서/구역(zone) 텔레메트리를 읽어온다.

프로토콜 (combined_smartfarm_robot.ino와 반드시 짝이 맞아야 함):
  파이 -> 아두이노 : "MV,<action>,<speed>\n"
  아두이노 -> 파이 : "BAT,<percent>,TEMP,<c>,DIST,<cm>,ZONE,<count>,STATUS,<상태>\n"
"""

import time

import serial


class MotionModule:
    SUPPORTED_ACTIONS = {
        "start_patrol", "resume_patrol", "pause_for_capture", "stop_patrol",
        "forward", "backward", "turn_left", "turn_right", "stop",
        "heartbeat",
    }

    def __init__(self, config):
        self.config = config
        self.ser = None
        self._latest_telemetry = None
        self._current_zone_count = 0
        # ★ 앱/서버가 이 로봇에게 "순찰 시작"을 시켰는지 스스로 기억한다.
        self._is_patrolling = False
        self._connect()

    # ── 연결 / 재연결 ──────────────────────────────────────
    def _connect(self):
        try:
            self.ser = serial.Serial(
                self.config["arduino_port"],
                self.config["arduino_baud"],
                timeout=1,
            )
            self.ser.dtr = False
            self.ser.rts = False
            time.sleep(2)
            print(f"✅ [Motion] 아두이노 연결 성공 ({self.config['arduino_port']})")
        except serial.SerialException as e:
            print(f"❌ [Motion] 아두이노 연결 실패: {e}. 텔레메트리/명령 전송 없이 동작합니다.")
            self.ser = None

    def _ensure_connected(self):
        if self.ser is None or not self.ser.is_open:
            self._connect()

    # ── ⭐ MQTT 모듈이 콜백으로 호출하는 진입점 (앱 -> 서버 -> Pi -> 아두이노) ──
    def handle_command(self, payload):
        """
        payload 예시 (서버 문서 3-4 규격):
          {"command": "start_patrol", "target_zone": "zone02", "timestamp": "..."}
        내부 테스트 도구와의 호환을 위해 "action" 키도 대비해서 읽는다.
        """
        action = payload.get("command", payload.get("action"))
        speed = payload.get("speed", 50)

        # ⚠️ target_zone(특정 구역 지정 이동)은 현재 펌웨어가 지원하지 않는다.
        target_zone = payload.get("target_zone")
        if target_zone:
            print(f"  [Motion 참고] target_zone={target_zone} 요청됐으나 "
                  f"현재 펌웨어는 특정 구역 지정 이동을 지원하지 않습니다 (무시됨, 향후 구현 필요).")

        if action not in self.SUPPORTED_ACTIONS:
            print(f"  [Motion 경고] 알 수 없는 명령: {action}")
            return

        self._ensure_connected()
        if self.ser is None:
            print("  [Motion 에러] 아두이노 미연결 상태라 명령을 보낼 수 없습니다.")
            return

        command_str = f"MV,{action},{speed}\n"
        try:
            self.ser.write(command_str.encode("utf-8"))
            print(f"  [Motion] 아두이노로 명령 전송: {command_str.strip()}")

            if action == "start_patrol":
                self._current_zone_count = 0

            # ★ 순찰 상태 스스로 기억
            if action in ("start_patrol", "resume_patrol"):
                self._is_patrolling = True
            elif action in ("stop_patrol", "stop"):
                self._is_patrolling = False

        except serial.SerialException as e:
            print(f"  [Motion 에러] 명령 전송 실패: {e}")
            self.ser = None

    # ── 앱이 실제로 "순찰 시작"을 시킨 적이 있는지 (PAUSE-BEFORE-CAPTURE에서 사용) ──
    def is_currently_patrolling(self):
        return self._is_patrolling

    # ── 🛡️ 안전 타임아웃용 하트비트 ──
    def send_heartbeat(self):
        self.handle_command({"command": "heartbeat"})

    # ── 아두이노가 보내는 배터리/센서/구역 데이터 읽기 ─────────────
    def read_telemetry(self):
        self._ensure_connected()
        if self.ser is None or self.ser.in_waiting == 0:
            return None

        try:
            line = self.ser.readline().decode("utf-8", errors="ignore").strip()
        except serial.SerialException as e:
            print(f"  [Motion 에러] 텔레메트리 읽기 실패: {e}")
            self.ser = None
            return None

        if not line or not line.startswith("ZONE"):
            return None

        telemetry = self._parse_telemetry(line)
        if telemetry is not None:
            self._latest_telemetry = telemetry
            if "zone_count" in telemetry:
                self._current_zone_count = int(telemetry["zone_count"])
            # ★ 물리 버튼으로 순찰이 켜지고 꺼진 경우까지 반영되도록,
            #   실제 아두이노 상태(STATUS)로 _is_patrolling을 동기화한다.
            if "operating_status" in telemetry:
                self._is_patrolling = telemetry["operating_status"] != "IDLE"

        return telemetry

    @staticmethod
    def _parse_telemetry(line):
        parts = line.split(",")
        if len(parts) % 2 != 0:
            print(f"  [Motion 경고] 텔레메트리 형식 오류, 원문: {line!r}")
            return None

        key_map = {
            "BAT": "battery_percent", "TEMP": "temperature_c",
            "DIST": "distance_cm", "ZONE": "zone_count",
            "STATUS": "operating_status", "HUM": "humidity_percent",
        }
        result = {}
        for i in range(0, len(parts), 2):
            key, value = parts[i], parts[i + 1]
            mapped_key = key_map.get(key)
            if mapped_key is None:
                continue
            if mapped_key == "operating_status":
                result[mapped_key] = value
                continue
            try:
                result[mapped_key] = float(value)
            except ValueError:
                continue

        return result or None

    # ── main_controller가 캡처 시점마다 호출해서 현재 구역을 얻어감 ──
    def get_current_zone(self):
        return f"zone_{self._current_zone_count}"

    def get_latest_telemetry(self):
        return self._latest_telemetry

    def close(self):
        if self.ser is not None and self.ser.is_open:
            self.ser.close()
