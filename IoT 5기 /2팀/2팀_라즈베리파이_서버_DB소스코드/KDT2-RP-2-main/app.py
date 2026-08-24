"""Smart Closet Backend 진입점

이 파일 자체는 로직을 거의 담고 있지 않다. FastAPI 앱을 만들고, 각
기능별 라우터를 등록하고, 서버가 시작될 때 DB/MQTT/카메라 스레드를
초기화하는 조립 역할만 한다. 실제 기능은 아래 모듈들에 나뉘어 있다.

- config.py             : 환경 변수, 경로, 각종 상수, 로깅/torch 설정
- database.py           : SQLite 읽기/쓰기 (옷장 DB, 컨텍스트, 추천 이력)
- mqtt_client.py        : 레일 제어 MQTT 발행
- gemini_service.py     : Gemini로 옷 사진 설명 생성
- qr_detector.py        : YOLO 기반 QR 인식
- clothing_detector.py  : YOLO 기반 상의 인식
- image_analysis.py     : 저장된 사진의 보조 라벨/로컬 요약
- recommendation.py     : 오늘 입을 옷 3벌을 고르는 로직
- camera_stream.py      : 카메라 캡처 + 인식 파이프라인 (백그라운드 스레드)
- routes_camera.py      : 밝기 조절 / 실시간 스트림 라우터
- routes_closet.py      : 옷장 조회 / 업로드 / 사진 다운로드 라우터
- routes_context.py     : 날씨/캘린더 컨텍스트 라우터
- routes_recommend.py   : 추천 / 레일 전송 라우터
- web_ui.py             : 브라우저용 홈 화면 라우터

systemd 서비스(smart-closet-streaming.service)가 이 파일을
`python3 -u app.py`로 그대로 실행하므로, 파일 이름과 `app` 변수 이름은
바꾸지 않는다.
"""

from __future__ import annotations

from fastapi import FastAPI

import camera_stream
import routes_camera
import routes_closet
import routes_context
import routes_recommend
import web_ui
from database import initialize_database
from mqtt_client import initialize_mqtt

app = FastAPI(title="Smart Closet Backend")

initialize_database()

app.include_router(web_ui.router)
app.include_router(routes_camera.router)
app.include_router(routes_closet.router)
app.include_router(routes_context.router)
app.include_router(routes_recommend.router)


@app.on_event("startup")
def on_startup() -> None:
    initialize_mqtt()
    camera_stream.start_camera_thread_once()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
