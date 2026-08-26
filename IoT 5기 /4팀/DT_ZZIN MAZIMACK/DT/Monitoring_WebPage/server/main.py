# main.py — IP 카메라(RTSP) 영상을 WebRTC로 브라우저에 직접 전달하는 서버
#
# 흐름:  IP 카메라 ──(RTSP)──▶ FastAPI + aiortc ──(WebRTC / WHEP)──▶ 브라우저 <video>
#
# MediaMTX 없이 이 서버가 WHEP 엔드포인트 역할을 직접 합니다.
#
# 엔드포인트
#   POST   /api/whep         : SDP offer(text/sdp)를 받아 answer를 돌려줍니다
#   DELETE /api/whep/{id}    : 세션 종료 (WHEP 리소스 해제)
#   GET    /api/status       : 카메라 연결 상태 / FPS / 시청자 수 (JSON)
#   GET    /api/snapshot     : 현재 프레임 한 장 (JPEG)
#
# 실행 방법 (둘 중 아무거나):
#     python main.py
#     uvicorn main:app --host 0.0.0.0 --port 8081

import asyncio
import contextlib
import io
import time
from collections import deque
from contextlib import asynccontextmanager
from fractions import Fraction
from uuid import uuid4

import av
import numpy as np
from aiortc import (
    RTCConfiguration,
    RTCIceServer,
    RTCPeerConnection,
    RTCRtpSender,
    RTCSessionDescription,
)
from aiortc.codecs import h264 as h264_codec
from aiortc.codecs import vpx as vpx_codec
from aiortc.contrib.media import MediaPlayer, MediaRelay
from aiortc.mediastreams import MediaStreamTrack, VideoStreamTrack
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

import config

VIDEO_CLOCK_RATE = 90000  # WebRTC 영상 타임스탬프의 표준 클럭

# ---------------------------------------------------------------- 비트레이트 상한 해제
# aiortc는 인코더 비트레이트를 모듈 상수로 묶어둡니다(VP8 1.5Mbps / H264 3Mbps).
# 이 상한 때문에 해상도를 올려도 화면이 뭉개지므로 설정값으로 올려줍니다.
# 인코더가 생성될 때 이 전역값을 읽으므로 앱 시작 전에 바꿔두면 됩니다.
#
# ※ aiortc 내부 상수를 직접 건드리는 방식입니다. aiortc를 올릴 때 이름이 바뀌지
#   않았는지 확인하세요. (공개 API로는 목표 비트레이트를 지정할 수 없습니다)
for _codec in (h264_codec, vpx_codec):
    _codec.DEFAULT_BITRATE = config.VIDEO_BITRATE
    _codec.MAX_BITRATE = config.VIDEO_BITRATE

# aiortc의 H264 인코더는 profile=Baseline, level=31로 고정되어 있습니다.
# level 3.1의 상한이 1280x720이라 그보다 크게 보내면 규격을 벗어납니다.
# 1080p로 내보내려면 VP8을 쓰세요 (PREFER_H264=0). VP8은 이런 제약이 없습니다.
H264_MAX_WIDTH = 1280
if config.PREFER_H264 and config.MAX_WIDTH > H264_MAX_WIDTH:
    print(
        f"[warn] MAX_WIDTH={config.MAX_WIDTH}는 H264 level 3.1 상한({H264_MAX_WIDTH})을 넘습니다.\n"
        f"       1080p가 필요하면 PREFER_H264=0으로 VP8을 쓰세요."
    )


# ============================================================== 카메라 소스
class CameraSource:
    """RTSP 연결을 혼자 담당합니다.

    가장 최근 프레임 한 장만 들고 있고, 연결이 끊기면 스스로 재연결합니다.
    브라우저에 나가는 트랙(CameraTrack)은 이 연결의 생사와 무관하게 계속 살아있으므로,
    카메라가 잠깐 끊겼다 돌아와도 WebRTC를 다시 맺을 필요가 없습니다.
    """

    def __init__(self):
        self.latest: av.VideoFrame | None = None
        self.connected = False
        self.last_error: str | None = None
        self.resolution: str | None = None
        self.last_frame_at = 0.0
        self._frame_times = deque(maxlen=30)

    @property
    def fps(self) -> float:
        if len(self._frame_times) < 2:
            return 0.0
        span = self._frame_times[-1] - self._frame_times[0]
        return (len(self._frame_times) - 1) / span if span > 0 else 0.0

    @property
    def seconds_since_frame(self) -> float | None:
        return time.time() - self.last_frame_at if self.last_frame_at else None

    def _mark(self, frame: av.VideoFrame):
        now = time.time()
        self.last_frame_at = now
        self._frame_times.append(now)
        if self.resolution is None:
            self.resolution = f"{frame.width}x{frame.height}"

    async def run(self):
        """연결 → 프레임 수신 → 끊기면 재연결. 서버가 사는 동안 계속 돕니다."""
        while True:
            player = None
            try:
                # av.open()은 블로킹입니다. 연결이 오래 걸릴 수 있어 스레드에서 엽니다.
                player = await asyncio.to_thread(
                    MediaPlayer,
                    config.RTSP_URL,
                    format=config.RTSP_FORMAT,
                    options=config.RTSP_OPTIONS,
                    timeout=config.OPEN_TIMEOUT,
                )
                if player.video is None:
                    raise RuntimeError("입력에 영상 트랙이 없습니다")

                print("[rtsp] 카메라 연결됨")
                self.connected = True
                self.last_error = None

                while True:
                    frame = await asyncio.wait_for(
                        player.video.recv(), timeout=config.FRAME_TIMEOUT
                    )
                    self.latest = frame
                    self._mark(frame)

            except asyncio.CancelledError:
                raise
            except Exception as exc:  # 연결 실패 · 수신 끊김 · 타임아웃 전부 여기로
                self.connected = False
                self.last_error = str(exc) or exc.__class__.__name__
                print(
                    f"[rtsp] 끊김: {self.last_error} — {config.RECONNECT_DELAY}초 후 재시도"
                )
            finally:
                if player is not None and player.video is not None:
                    player.video.stop()

            await asyncio.sleep(config.RECONNECT_DELAY)


# ============================================================== 송출 트랙
class CameraTrack(VideoStreamTrack):
    """브라우저로 나가는 영상 트랙.

    소스가 끊겨도 이 트랙은 끝나지 않습니다. 프레임이 없으면 검은 화면을 내보내
    WebRTC 연결을 유지하고, 카메라가 살아나면 영상이 그대로 이어집니다.
    (트랙이 끝나버리면 브라우저가 재협상을 해야 하는데, 그게 훨씬 번거롭습니다.)

    ▶ 나중에 YOLO를 붙일 자리: `_render()`에서 frame → ndarray로 바꿔 추론하고
      바운딩 박스를 그린 뒤 다시 VideoFrame으로 만들면 됩니다.
    """

    def __init__(self, source: CameraSource):
        super().__init__()
        self._source = source
        self._count = 0
        self._start: float | None = None
        self._blank: np.ndarray | None = None

    async def recv(self):
        pts, time_base = await self._next_timestamp()
        frame = self._render()
        frame.pts = pts
        frame.time_base = time_base
        return frame

    async def _next_timestamp(self):
        """TARGET_FPS에 맞춰 송출 속도를 조절합니다."""
        if self._start is None:
            self._start = time.time()
            self._count = 0
        else:
            self._count += 1
            delay = (self._start + self._count / config.TARGET_FPS) - time.time()
            if delay > 0:
                await asyncio.sleep(delay)
            elif delay < -1.0:
                # 시청자가 없어 한동안 쉬었다 재개된 경우.
                # 밀린 프레임을 몰아 보내지 않도록 시계를 현재 시각으로 맞춥니다.
                self._start = time.time() - self._count / config.TARGET_FPS
        pts = int(self._count * VIDEO_CLOCK_RATE / config.TARGET_FPS)
        return pts, Fraction(1, VIDEO_CLOCK_RATE)

    def _render(self) -> av.VideoFrame:
        frame = self._source.latest
        age = self._source.seconds_since_frame
        if frame is None or age is None or age > config.STALE_AFTER:
            return self._blank_frame()
        return self._scale(frame)

    def _scale(self, frame: av.VideoFrame) -> av.VideoFrame:
        # yuv420p는 가로·세로가 짝수여야 합니다.
        if config.MAX_WIDTH and frame.width > config.MAX_WIDTH:
            width = config.MAX_WIDTH - (config.MAX_WIDTH % 2)
            height = int(frame.height * width / frame.width)
            height -= height % 2
            return frame.reformat(width=width, height=height, format="yuv420p")
        return frame.reformat(format="yuv420p")

    def _blank_frame(self) -> av.VideoFrame:
        if self._blank is None:
            width = (config.MAX_WIDTH or 960) & ~1
            height = (width * 9 // 16) & ~1
            self._blank = np.full((height, width, 3), 18, dtype=np.uint8)
        # 매번 새 프레임을 만듭니다. 같은 객체를 재사용하면 인코더 큐에 남아있는
        # 프레임의 pts를 덮어쓰게 됩니다.
        return av.VideoFrame.from_ndarray(self._blank, format="bgr24").reformat(
            format="yuv420p"
        )


camera = CameraSource()
camera_track = CameraTrack(camera)
# 하나의 소스를 여러 시청자에게 나눠줍니다. (RTSP 연결은 계속 1개)
relay = MediaRelay()

class Session:
    """시청자 한 명. last_seen은 /api/status 호출로 갱신됩니다."""

    def __init__(self, pc: RTCPeerConnection, track: MediaStreamTrack):
        self.pc = pc
        self.track = track
        self.last_seen = time.time()


sessions: dict[str, Session] = {}


async def close_session(session_id: str):
    session = sessions.pop(session_id, None)
    if session is None:
        return
    session.track.stop()  # relay 구독 해제 — 안 하면 시청자가 나가도 계속 인코딩합니다
    await session.pc.close()
    print(f"[whep] {session_id[:8]} 종료 (남은 시청자 {len(sessions)}명)")


async def reap_sessions():
    """하트비트가 끊긴 세션을 회수합니다.

    브라우저가 죽거나, 네트워크가 끊기거나, 탭이 강제 종료되면 DELETE가 오지 않고
    WebRTC 연결도 한동안 'connected'로 남아있습니다. 그동안 인코더가 계속 도므로
    소식이 없는 세션은 서버가 직접 정리합니다.
    """
    while True:
        await asyncio.sleep(5)
        cutoff = time.time() - config.SESSION_TIMEOUT
        stale = [sid for sid, s in sessions.items() if s.last_seen < cutoff]
        for session_id in stale:
            print(f"[whep] {session_id[:8]} 하트비트 끊김 — 회수")
            await close_session(session_id)


# ============================================================== 앱
@asynccontextmanager
async def lifespan(app: FastAPI):
    tasks = [asyncio.create_task(camera.run()), asyncio.create_task(reap_sessions())]
    print(f"[server] 준비 완료 — http://localhost:{config.SERVER_PORT}/api/status")
    yield
    for task in tasks:
        task.cancel()
    for task in tasks:
        with contextlib.suppress(asyncio.CancelledError):
            await task
    for session_id in list(sessions):
        await close_session(session_id)
    print("[server] 종료")


app = FastAPI(lifespan=lifespan, title="SENTRY CCTV WebRTC")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    # 브라우저가 세션 종료용 Location 헤더를 읽을 수 있어야 합니다.
    expose_headers=["Location"],
)


# ---------------------------------------------------------------- WHEP
@app.post("/api/whep")
async def whep(request: Request):
    """브라우저의 SDP offer를 받아 answer를 돌려줍니다 (WHEP)."""
    offer_sdp = (await request.body()).decode()

    ice_servers = [RTCIceServer(urls=url) for url in config.STUN_SERVERS]
    pc = RTCPeerConnection(RTCConfiguration(iceServers=ice_servers))
    session_id = uuid4().hex

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print(f"[whep] {session_id[:8]} → {pc.connectionState}")
        if pc.connectionState in ("failed", "closed", "disconnected"):
            await close_session(session_id)

    # 코덱 우선순위를 H264로 바꿉니다. 같은 비트레이트에서 VP8보다 화질이 좋습니다.
    #
    # ※ 순서가 중요합니다. aiortc는 setRemoteDescription 시점에 사용할 코덱을 확정하므로
    #   그 전에 트랜시버를 만들어 두고 우선순위를 지정해야 합니다.
    #   (offer가 만들어준 트랜시버에 나중에 지정하면 이미 늦어서 무시됩니다)
    video = pc.addTransceiver("video", direction="sendonly")
    if config.PREFER_H264:
        codecs = RTCRtpSender.getCapabilities("video").codecs
        h264 = [c for c in codecs if c.mimeType == "video/H264"]
        if h264:
            video.setCodecPreferences(h264 + [c for c in codecs if c.mimeType != "video/H264"])

    await pc.setRemoteDescription(RTCSessionDescription(sdp=offer_sdp, type="offer"))

    # 위에서 만든 트랜시버(아직 트랙 없음)에 우리 영상이 붙습니다.
    track = relay.subscribe(camera_track)
    pc.addTrack(track)
    sessions[session_id] = Session(pc, track)

    answer = await pc.createAnswer()
    # aiortc는 trickle ICE를 쓰지 않습니다.
    # setLocalDescription이 ICE 후보 수집이 끝날 때까지 기다렸다가 완성된 SDP를 만듭니다.
    await pc.setLocalDescription(answer)

    print(f"[whep] {session_id[:8]} 시작 (시청자 {len(sessions)}명)")
    return Response(
        content=pc.localDescription.sdp,
        status_code=201,
        media_type="application/sdp",
        headers={"Location": f"/api/whep/{session_id}"},
    )


@app.delete("/api/whep/{session_id}")
async def whep_delete(session_id: str):
    await close_session(session_id)
    return Response(status_code=204)


# ---------------------------------------------------------------- 상태 / 스냅샷
@app.get("/api/status")
def status(session: str | None = None):
    # 시청자가 자기 세션 id를 함께 보내면 하트비트로 처리합니다.
    if session and session in sessions:
        sessions[session].last_seen = time.time()

    age = camera.seconds_since_frame
    return {
        "camera_connected": camera.connected,
        "fps": round(camera.fps, 1),
        "viewers": len(sessions),
        "resolution": camera.resolution,
        "seconds_since_frame": round(age, 1) if age is not None else None,
        "error": camera.last_error,
    }


@app.get("/api/snapshot")
def snapshot():
    """현재 프레임 한 장(JPEG). 이벤트 스냅샷 등에 쓸 수 있습니다."""
    frame = camera.latest
    if frame is None:
        return Response(status_code=503)
    buffer = io.BytesIO()
    frame.to_image().save(buffer, format="JPEG", quality=80)
    return Response(
        buffer.getvalue(),
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store"},
    )


# ---------------------------------------------------------------- 센서 실시간 데이터 (WebSocket)
# ▶ 여기서 개발하세요 (추후 데이터 통신)
#
#   센서(MQ2/불꽃/온도) ──▶ 수집 장치 ──▶ 이 서버 ──(WebSocket)──▶ 브라우저 대시보드
#
# 프런트엔드는 hooks/useSensorSocket.js 에서 이 엔드포인트에 연결하고,
# 구역별 "상대 세기(0~100)" 값을 받아 화면에 표시합니다.
# (실제 ppm 농도 계산은 하지 않고 센서 출력의 상대 세기만 0~100으로 정규화)
#
# 브라우저가 기대하는 메시지 형태(예시):
#   {
#     "Zone A": {"intensity": 0~100, "flame": "감지"|"미감지", "temp": "23.4", "level": "정상"|"주의"|"위험"},
#     "Zone B": {...}, ...
#   }
#
# 아래는 개발을 시작할 자리를 표시하는 스켈레톤입니다. (현재는 주석 처리)
# 센서 데이터 소스가 정해지면 주석을 풀고 실제 값을 push 하세요.
#
# from fastapi import WebSocket, WebSocketDisconnect
#
# @app.websocket("/ws/sensors")
# async def ws_sensors(websocket: WebSocket):
#     await websocket.accept()
#     try:
#         while True:
#             # TODO: 실제 센서값을 읽어 0~100 상대 세기로 정규화한 뒤 내보냅니다.
#             readings = {
#                 "Zone A": {"intensity": 15, "flame": "미감지", "temp": "23.4", "level": "정상"},
#                 # ...
#             }
#             await websocket.send_json(readings)
#             await asyncio.sleep(1)  # 전송 주기
#     except WebSocketDisconnect:
#         pass


# ---------------------------------------------------------------- 실행 진입점
# 이게 없으면 `python main.py`가 app만 정의하고 곧바로 종료합니다.
# (에러도 안 나고 그냥 꺼져서 원인을 찾기 어렵습니다)
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.SERVER_HOST, port=config.SERVER_PORT)
