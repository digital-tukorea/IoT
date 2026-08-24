# archive/

더 이상 사용하지 않는 이전 프로토타입 스케치를 참고용으로 보관합니다.
**실제 빌드/업로드에는 사용하지 마세요.** 최종 스케치는 `arduino_sketch/combined_smartfarm_robot.ino`입니다.

- `original.cpp` — (2026-08-06 교체됨) 하드웨어 담당자의 WiFi/MQTT 직접 연결 테스트 빌드.
  라인트레이싱 + 마커 감지 + 왕복 주행(U턴) + 물리 버튼 로직이 검증된 상태로,
  이 로직은 `combined_smartfarm_robot.ino`에 GPIO 시리얼 통신 방식으로 이식되었습니다.
  통신 계층(WiFi/MQTT)만 참고하지 말고 실제 코드는 최종 스케치를 사용하세요.
