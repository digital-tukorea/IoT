# CCTV 스트리밍 서버 (WebRTC)

IP 카메라(RTSP) 영상을 WebRTC로 대시보드에 전달합니다. MediaMTX 없이 FastAPI가 WHEP 서버 역할을 직접 합니다.

```
IP 카메라 ──(RTSP)──▶ FastAPI + aiortc ──(WebRTC / WHEP)──▶ 브라우저 <video>
```

## 설치

```bash
cd server
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 카메라 주소 설정

`config.py`의 `RTSP_URL`을 직접 고치거나, 환경변수로 넘깁니다(권장 — 비밀번호가 커밋되지 않습니다).

```powershell
$env:RTSP_URL = "rtsp://admin:1234@192.168.0.100:554/stream1"
```

카메라가 아직 없다면 동영상 파일 경로로도 테스트할 수 있습니다. Windows 웹캠을 쓰려면
`RTSP_URL="video=<장치이름>"`, `RTSP_FORMAT="dshow"`로 설정하세요.
장치 이름은 `ffmpeg -list_devices true -f dshow -i dummy`로 확인합니다.

## 실행

`server` 폴더 안에서, 가상환경을 켠 뒤 실행합니다.
CCTV 스트리밍 서버는 로컬 테스트 중 **8081**을 씁니다.

```bash
python main.py
```

uvicorn을 직접 부르고 싶다면 (코드 수정 시 자동 재시작이 필요할 때 `--reload`):

```bash
uvicorn main:app --host 0.0.0.0 --port 8081
```

| 엔드포인트 | 설명 |
| --- | --- |
| `POST /api/whep` | SDP offer → answer (WebRTC 시그널링) |
| `DELETE /api/whep/{id}` | 세션 종료 |
| `GET /api/status` | 연결 상태 · FPS · 시청자 수 (`?session=<id>`를 붙이면 하트비트) |
| `GET /api/snapshot` | 현재 프레임 한 장 (JPEG) |

프론트를 붙이기 전에 `http://localhost:8081/api/status`를 열어 `camera_connected: true`인지 먼저 확인하세요.
여기가 false면 원인은 카메라/RTSP 쪽이고, true인데 화면이 안 나오면 WebRTC 쪽입니다.

### 실행하자마자 꺼질 때

| 증상 | 원인 |
| --- | --- |
| 아무 것도 안 찍히고 즉시 종료 | 옛날 `main.py`에는 실행 진입점이 없어서 `python main.py`가 그냥 끝났습니다. 지금은 해결됨 |
| `ModuleNotFoundError: config` | `server` 폴더 밖에서 실행했습니다. `cd server` 후 실행하세요 |
| `ModuleNotFoundError: aiortc` | 가상환경을 안 켰습니다. `.venv\Scripts\activate` |
| `address already in use` | 8081번 포트를 이미 쓰고 있습니다. 이전 서버를 끄거나 `SERVER_PORT`를 바꾸세요 |

## 화질 조정

화질은 세 가지가 결정합니다. 위에서부터 영향이 큽니다.

**1. 카메라가 주는 원본** — 경로 끝 숫자가 스트림을 고릅니다.

| 경로 | 해상도 | 용도 |
| --- | --- | --- |
| `/0` | 1920x1080 | 화면 출력 (기본값) |
| `/1` | 720x480 | 나중에 YOLO 추론용으로 쓰기 좋음 |

**2. 송출 해상도·비트레이트** (`config.py`)

```python
MAX_WIDTH = 1280        # 화면에 띄우는 크기 기준으로 충분
VIDEO_BITRATE = 4000000 # aiortc 기본 상한(VP8 1.5M / H264 3M)을 풀어줌
TARGET_FPS = 15
```

1080p로 내보내려면 `MAX_WIDTH=1920` + `PREFER_H264=0`이 필요합니다.
aiortc의 H264 인코더가 level 3.1(=1280x720 상한)로 고정되어 있어서, 그 이상은 VP8로 보내야 합니다.

**3. 화면에 맞추는 방식** — `LiveCctv`의 `objectFit`이 기본 `contain`입니다.
`cover`로 바꾸면 컨테이너를 꽉 채우지만 화면 위아래가 잘립니다. 관제용이라 전체를 보이는 쪽을 기본으로 했습니다.

## CPU가 튀거나 영상이 버벅일 때

aiortc는 **파이썬 소프트웨어 인코더**를 쓰고, **시청자 1명당 인코더가 하나씩** 돕니다.
다만 실측으로는 1080p H264가 프레임당 4ms 수준이라, 보통은 CPU보다 대역폭이 먼저 문제가 됩니다.
그래도 부족하면 `MAX_WIDTH`와 `TARGET_FPS`를 낮추세요.

## 세션 정리 방식

브라우저가 정상적으로 나가면 `DELETE /api/whep/{id}`로 세션이 닫힙니다.
하지만 탭이 강제 종료되거나 네트워크가 끊기면 그 요청이 오지 않고, WebRTC 연결도
한동안 `connected`로 남아 인코더가 계속 돕니다.

그래서 시청자는 `/api/status?session=<id>`로 3초마다 하트비트를 보내고,
서버는 `SESSION_TIMEOUT`(기본 20초) 동안 소식이 없는 세션을 직접 회수합니다.
`viewers` 값이 실제 보고 있는 창 수와 맞는지로 확인할 수 있습니다.

## 나중에 YOLO를 붙일 자리

`main.py`의 `CameraTrack._render()`입니다. 여기서 `frame.to_ndarray(format="bgr24")`로 바꿔
추론하고, 바운딩 박스를 그린 뒤 `av.VideoFrame.from_ndarray()`로 되돌리면 영상에 결과가 얹힙니다.
