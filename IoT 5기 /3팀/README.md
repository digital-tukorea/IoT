[Uploading README.md…]()

# SMART MOTION DESK - SMATY
책상 앞에 앉은 사용자를 알아보고, 말을 걸면 대답하고, 작업 모드에 맞춰 높이와 조명을 스스로 맞춥니다. 서버는 메인 서버와 영상 처리 서버로 구성되며, 메인 서버는 FastAPI, 조명 & 카메라 등 하드웨어 제어와 AI 스피커 등을 관리합니다. 영상 처리 서버는 사용자 인식, 기상 감지 등 영상 처리를 담당하며, 데이터를 저장하지 않는 State-less 서버입니다.

```text
        🎙 음성            📷 카메라            🖥 대시보드
          │                   │                    │
          └───────────► SMART DESK 서버 ◄──────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
         책상 높이·틸트     LED 조명        사용자 프로필
        (ESP32 / Arduino)   (WLED)         (모드·기억)
```

## 주요 기능

- **AI 음성 비서** — `하이 스마티` 호출어로 깨어나 사용자와 대화하고, 처리하고, 기억합니다.
- **책상 제어** — 목표 높이 이동, 수동 UP/DOWN, 상판 틸팅, 안전 정지를 지원합니다.
- **사용자 인식** — 카메라로 현재 사용자를 식별해 프로필별 설정을 자동으로 적용합니다.
- **작업 모드** — 독서·공부처럼 모드를 만들고 앉기/서기 높이와 LED 색을 저장합니다.
- **책상 위 인식** — 요청이 책상 위 내용에 달려 있으면 AI가 workspace 카메라의 최신 화면을 직접 보고 답합니다.
- **자동화** — 자세와 착석 상태를 보고 자세에 맞춰 책상을 움직입니다.
- **웹 대시보드** — React 화면에서 상태 확인과 제어, 프로필·모드 관리를 합니다.
- **장기 기억** — 사용자와의 대화를 기억하여 할일 안내, 업무 보조를 지원합니다.

## 구성 요소

| 영역 | 내용 |
| --- | --- |
| 백엔드 | Python 3.11+ / FastAPI / asyncio (단일 프로세스, worker 1개) |
| 프런트엔드 | React 19 + TypeScript + Vite |
| 메시징 | EMQX (MQTT) — 서버와 ESP32 사이 통신 |
| 영상 | MediaMTX + µStreamer — 카메라 스트림 중계 |
| 펌웨어 | ESP32-WROOM-32E(높이 relay·틸트), Arduino(높이 센서 읽기) |
| 데이터 | SQLite (프로필·모드·사용 이력), Mem0 (장기 기억) |
| 외부 | OpenAI Realtime (음성), WLED (조명) |

## 컨테이너 구조

```text
                     ┌─────────────────────────────┐
                     │      fin-internal 네트워크   │
                     │                             │
  브라우저 :9090 ───► │  main ──────► emqx :1883 ───┼──► ESP32 (Wi-Fi)
                     │   │  ▲                      │
  음성 디버그 :10000 ─►│   │  └── vision :9091      │
                     │   │            ▲            │
                     │   │      mjpeg-user-cam ────┼──► USB 카메라
                     │   └──► mediamtx :8889       │
                     └─────────────────────────────┘
                            │
                       ../data (SQLite·Mem0)
```

| 서비스 | 이미지 | 역할 |
| --- | --- | --- |
| `main` | 로컬 빌드 (`main-runtime`) | FastAPI API + React 대시보드 + 음성 비서. 책상·조명·프로필의 중심. |
| `emqx` | `emqx/emqx` | MQTT 브로커. 서버와 ESP32가 여기서 만납니다. |
| `mediamtx` | `bluenviron/mediamtx` | WebRTC 영상 중계. 브라우저가 카메라를 볼 때 사용합니다. |
| `mjpeg-user-cam` | `mkuf/ustreamer` | USB 카메라의 MJPEG 프레임을 재인코딩 없이 그대로 넘깁니다. |
| `vision` | 로컬 빌드 (`vision-runtime`) | 얼굴·자세 인식 전용 서버. 선택 서비스이며 다른 장비에서 돌릴 수 있습니다. |

이미지는 [`Dockerfile`](Dockerfile) 하나에서 멀티스테이지로 만들고, 프런트엔드 빌드와
Python 의존성 설치를 분리해 코드 수정만으로 무거운 재설치가 일어나지 않게 했습니다.

`main` 컨테이너는 호스트의 오디오 장치와 Arduino 시리얼 포트를 넘겨받고, 데이터는
`data/` 디렉터리에 남습니다. `vision`은 GPU/CPU 여유가 있는 장비로 떼어내
[`deploy/compose.vision-remote.yml`](deploy/compose.vision-remote.yml)로 따로 띄울 수 있습니다.

## 시작하기

### 요구 사항

- Python 3.11 이상, Node.js 22 이상
- Docker / Docker Compose (컨테이너 배포 시)
- MQTT 브로커(EMQX) — 서버 시작에 필수입니다

### 개발 환경

```bash
git clone <repository-url> smart-desk-fin
cd smart-desk-fin

python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'

cd frontend && npm ci && cd ..
```

설정 값은 [`.env.example`](.env.example)을 복사해 `.env`로 사용합니다. 같은 이름의
환경변수가 있으면 그 값이 우선합니다.

```bash
cp .env.example .env
```

### 실행

브로커가 `127.0.0.1:1883`에 떠 있는지 확인한 뒤 백엔드를 실행합니다.

```bash
.venv/bin/uvicorn smart_desk.main:app --host 0.0.0.0 --port 9090 --workers 1
```

다른 터미널에서 대시보드 개발 서버를 실행하고 `http://127.0.0.1:5173`을 엽니다.

```bash
cd frontend && npm run dev
```

> 하드웨어 제어 객체가 프로세스마다 하나씩만 존재해야 하므로 worker는 항상 1개이며,
> 실제 책상이 연결된 상태에서는 `--reload`를 쓰지 않습니다.

### 상태 확인

```bash
curl http://127.0.0.1:9090/health/live    # 프로세스 생존
curl http://127.0.0.1:9090/health/ready   # 기동 완료 여부
curl http://127.0.0.1:9090/api/status     # 책상·연결 상태
```

## 배포

전체 스택을 Compose로 올립니다. 라즈베리파이에서는 두 파일을 함께 지정합니다.

```bash
sudo docker compose --env-file .env \
  -f deploy/compose.yml \
  -f deploy/compose.raspberry-pi.yml \
  up -d --build
```

서비스 하나만 다시 배포할 때:

```bash
sudo docker compose --env-file .env \
  -f deploy/compose.yml -f deploy/compose.raspberry-pi.yml \
  stop main && \
sudo docker compose --env-file .env \
  -f deploy/compose.yml -f deploy/compose.raspberry-pi.yml \
  up -d --build main
```

상태와 로그:

```bash
sudo docker compose -f deploy/compose.yml ps
sudo docker logs --since 10m smart-desk-main-1
```

얼굴·자세 인식을 다른 장비에서 돌리려면 `vision` 프로필을 빼고 원격 Compose 파일을
사용합니다. 배포 뒤 확인할 URL과 복구 절차는 [운영 runbook](docs/operations/README.md)에
정리돼 있습니다.

컨테이너를 쓰지 않을 때는 프런트엔드를 먼저 빌드한 뒤 백엔드만 실행합니다.

```bash
cd frontend && npm run build && cd ..
.venv/bin/uvicorn smart_desk.main:app --host 0.0.0.0 --port 9090 --workers 1
```
