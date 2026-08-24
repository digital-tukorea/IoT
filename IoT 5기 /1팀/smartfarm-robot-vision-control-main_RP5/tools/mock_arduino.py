"""
mock_arduino.py
진짜 아두이노 대신 PC에서 시리얼 통신을 흉내내는 mock 스크립트. (테스트용)

★ 오늘 원복: 아두이노가 GPIO(UART) 시리얼로 라즈베리파이와 직접 연결되는
  것으로 확정되어, 시리얼/socat 기반 mock으로 되돌렸다. 텔레메트리에
  ZONE 필드가 추가되었다 (일정 시간마다 자동으로 zone이 증가하도록 흉내냄).

⭐ 사전 준비: socat으로 가상 시리얼 포트 쌍을 먼저 만들어야 한다.
  (socat 설치: sudo apt install socat / brew install socat)

  터미널 1 (가상 포트 생성, 계속 켜둔 채로 유지):
    socat -d -d pty,raw,echo=0,link=/tmp/ttyPI pty,raw,echo=0,link=/tmp/ttyARDUINO

  터미널 2 (이 스크립트 실행 - 아두이노 역할):
    python tools/mock_arduino.py

  config.py의 "arduino_port"를 "/tmp/ttyPI"로 임시 변경한 뒤
  터미널 3에서 main_controller.py를 실행하면, motion_module.py가
  이 mock_arduino.py를 진짜 아두이노처럼 통신 상대로 인식한다.
"""

import time
import random

import serial

MOCK_PORT = "/tmp/ttyARDUINO"
BAUD = 115200  
TELEMETRY_INTERVAL_SEC = 2      # 텔레메트리 전송 주기 (배터리/온도/거리/구역)
ZONE_CHANGE_INTERVAL_SEC = 12   # 테스트 편의를 위해 일정 시간마다 zone을 자동으로 증가시킴
HOME_LAP_ZONE_COUNT = 5         # 이 개수만큼 지나면 홈으로 돌아온 것처럼 0으로 리셋

zone_count = 0 #현재 구역이 어디인지
is_running = False #주행중 확인
last_zone_change_time = time.time()


def main():
    global zone_count, is_running, last_zone_change_time

    try:
        ser = serial.Serial(MOCK_PORT, BAUD, timeout=1)
    except serial.SerialException as e:
        print(f"❌ 가상 포트 연결 실패: {e}")
        print("먼저 socat으로 가상 시리얼 포트를 만들었는지 확인하세요.")
        return

    print(f"✅ [Mock 아두이노] {MOCK_PORT}에서 대기 중...")
    last_telemetry_time = time.time()

    try:
        while True:
            # ── 파이(motion_module.py)가 보낸 명령 수신 ──
            if ser.in_waiting > 0:
                line = ser.readline().decode("utf-8", errors="ignore").strip()
                if line:
                    print(f"📩 [명령 수신] {line}")
                    if "start_patrol" in line:
                        is_running = True
                        zone_count = 0
                        print("▶️ [Mock 아두이노] 순찰 시작 (zone 초기화)")
                    elif "stop" in line:
                        is_running = False
                        print("⏸️ [Mock 아두이노] 정지")

            # ── 테스트 편의: 일정 시간마다 자동으로 다음 구역으로 이동한 것처럼 흉내 ──
            now = time.time()
            if is_running and now - last_zone_change_time >= ZONE_CHANGE_INTERVAL_SEC:
                last_zone_change_time = now
                if zone_count >= HOME_LAP_ZONE_COUNT:
                    zone_count = 0
                    print("📍 [Mock 아두이노] 홈 마커 통과 -> zone 리셋")
                else:
                    zone_count += 1
                    print(f"📍 [Mock 아두이노] 구역 마커 통과 -> zone_{zone_count}")

            # ── 텔레메트리(배터리/온도/거리/구역) 흉내내서 전송 ──
            if now - last_telemetry_time >= TELEMETRY_INTERVAL_SEC:
                last_telemetry_time = now
                battery = round(random.uniform(60, 95), 1)
                temp = round(random.uniform(20, 30), 1)
                dist = round(random.uniform(10, 100), 1)
                telemetry = f"BAT,{battery},TEMP,{temp},DIST,{dist},ZONE,{zone_count}\n"
                ser.write(telemetry.encode("utf-8"))
                print(f"📤 [텔레메트리 전송] {telemetry.strip()}")

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n종료합니다")
    finally:
        ser.close()


if __name__ == "__main__":
    main()
