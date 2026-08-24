# smartfarm_robot (최종본)

모듈화된 스마트팜 로봇 제어 프로그램. 비전 인식/이동 제어/MQTT 통신/HTTP 업로드가
각각 독립 모듈로 분리되어 있고, `main_controller.py`가 이들을 조율한다.

## 최종 아키텍처 요약

- **YOLO(4클래스)**: 작물 종류만 탐지(eggplant/grape/strawberry/k_melon)
- **색상 분석**: 병해충 유/무 1차 판단 + 익음도(%) 계산 + 급변 조기경보(보조)
- **통신**: 이미지=HTTP, 나머지 메타데이터=MQTT로 분리, `batch_id`로 서버에서 매칭
- **성능**: 비동기(백그라운드 스레드) 추론 + imgsz=1280
- **배포**: AWS 서버 기준 MQTT(TLS)/HTTP 통신

## 실행 전 준비

1. 라이브러리 설치
   ```bash
   pip install ultralytics opencv-python numpy paho-mqtt requests pyserial
   ```

2. `models/` 폴더 확인
   - `models/best.pt` — 4클래스로 학습된 YOLO 가중치
   - `models/class_map.json` — `{"eggplant":0,"grape":1,"strawberry":2,"k_melon":3}`

3. `config.py`에서 `TODO` 표시된 값 실제 값으로 교체
   - `mqtt_broker`, `mqtt_username`, `mqtt_password` — AWS 서버 주소/인증정보
   - `http_upload_url` — AWS 서버의 업로드 엔드포인트
   - `disease_api_url`, `disease_api_key` — 병해충 판별 상위 AI API (예외처리용)
   - `CROP_COLOR_PROFILES`의 `disease_threshold` — calibrate_color_profiles.py로 재보정 권장

4. 실행
   ```bash
   python main_controller.py
   ```

## 남은 작업 (다음 단계)

- `target_zone`(특정 구역 지정 복귀) 아두이노 펌웨어 구현
- `CROP_COLOR_PROFILES`의 `disease_threshold` 실측 보정
- AWS 서버 실제 배포 후 `config.py` TODO 값 교체
