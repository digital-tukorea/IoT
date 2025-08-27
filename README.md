# IoT
IoT 스마트 융합 프로젝트 과정 파일 저장소입니다.
안녕하세요 테스트 해봅니다。



#🌫️ ESP32 IoT Dust Sensor Project

ESP32 + 먼지 센서(GP2Y1010AU0F) + MQTT 연동 프로젝트  
실시간 먼지 농도를 측정하여 MQTT 브로커로 전송하고,  
원격으로 팬(릴레이)을 제어합니다.

## ⚡ 하드웨어 연결
- DUST_SENSOR_LED_PIN → GPIO 26
- DUST_SENSOR_AOUT_PIN → GPIO 34 (ADC)
- RELAY_PIN → GPIO 25

## 🔌 네트워크
- WiFi SSID: `1team`
- MQTT Broker: `34.64.79.139`
- Publish: `sensor/dust`
- Subscribe: `/control/fan`

## 🚀 실행 방법
1. `src/main.ino`를 Arduino IDE로 열기
2. ESP32 보드 선택 후 업로드
3. 시리얼 모니터와 MQTT 클라이언트로 데이터 확인
