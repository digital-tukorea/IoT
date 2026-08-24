"""카메라/스트리밍 라우터

밝기 조절 API와 MJPEG 실시간 스트림(/video_feed, /video_feed/view)을
제공한다. 실제 프레임 캡처/인식은 camera_stream 모듈이 백그라운드
스레드에서 계속 갱신해 두고, 여기서는 그 최신 값을 읽어 응답할 뿐이다.
"""

from __future__ import annotations

import time
from typing import Iterable

import cv2
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

import camera_stream
from config import STREAM_FRAME_DELAY_SECONDS, STREAM_JPEG_QUALITY

router = APIRouter()


@router.get("/api/camera/brightness")
def get_camera_brightness() -> JSONResponse:
    with camera_stream.brightness_lock:
        brightness = camera_stream.stream_brightness
    return JSONResponse(content={"brightness": brightness, "min": -100, "max": 100})


@router.post("/api/camera/brightness")
def set_camera_brightness(value: int) -> JSONResponse:
    if not -100 <= value <= 100:
        raise HTTPException(status_code=400, detail="Brightness must be between -100 and 100")
    with camera_stream.brightness_lock:
        camera_stream.stream_brightness = value
    return JSONResponse(content={"brightness": camera_stream.stream_brightness})


@router.get("/video_feed")
def video_feed() -> StreamingResponse:
    def generate_frames() -> Iterable[bytes]:
        while True:
            try:
                with camera_stream.frame_lock:
                    frame = None if camera_stream.latest_frame is None else camera_stream.latest_frame.copy()

                if frame is None:
                    frame = camera_stream.create_placeholder_frame("Camera unavailable")

                try:
                    success, buffer = cv2.imencode(
                        ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), STREAM_JPEG_QUALITY]
                    )
                    if not success:
                        time.sleep(STREAM_FRAME_DELAY_SECONDS)
                        continue
                except Exception:
                    time.sleep(STREAM_FRAME_DELAY_SECONDS)
                    continue

                payload = buffer.tobytes()
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + payload + b"\r\n"
                )
                time.sleep(STREAM_FRAME_DELAY_SECONDS)
            except Exception:
                time.sleep(STREAM_FRAME_DELAY_SECONDS)

    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.get("/video_feed/view")
def video_feed_view() -> HTMLResponse:
    html = """
    <!doctype html>
    <html lang="ko">
        <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>Camera Stream</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 0;
                    min-height: 100vh;
                    display: grid;
                    place-items: center;
                    background: linear-gradient(135deg, #f7f7f7, #e8eef7);
                    color: #1f2937;
                }
                .card {
                    background: white;
                    padding: 24px;
                    border-radius: 16px;
                    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
                    max-width: 720px;
                    width: calc(100% - 32px);
                }
                h1 { margin-top: 0; font-size: 20px; }
                .hint {
                    color: #6b7280;
                    font-size: 13px;
                    margin: 4px 0 16px;
                }
                .stream-wrap {
                    position: relative;
                    border-radius: 12px;
                    overflow: hidden;
                    background: #000;
                    cursor: ns-resize;
                    user-select: none;
                }
                .stream-wrap img {
                    display: block;
                    width: 100%;
                    height: auto;
                }
                .badge {
                    position: absolute;
                    top: 10px;
                    right: 10px;
                    padding: 6px 12px;
                    border-radius: 999px;
                    background: rgba(17, 24, 39, 0.7);
                    color: white;
                    font-size: 13px;
                    font-variant-numeric: tabular-nums;
                    pointer-events: none;
                }
                .controls {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    margin-top: 14px;
                }
                .controls input[type=range] { flex: 1; }
                .controls button {
                    padding: 8px 14px;
                    border-radius: 10px;
                    border: 1px solid #d1d5db;
                    background: #f9fafb;
                    cursor: pointer;
                    font-size: 13px;
                }
                .controls button:hover { background: #f3f4f6; }
            </style>
        </head>
        <body>
            <main class="card">
                <h1>카메라 스트림</h1>
                <p class="hint">영상 위에서 마우스를 드래그하면(위로: 밝게 / 아래로: 어둡게) 조도가 조절됩니다. 휠로도 미세 조정할 수 있습니다.</p>
                <div class="stream-wrap" id="streamWrap">
                    <img id="stream" src="/video_feed" alt="camera stream" draggable="false" />
                    <div class="badge" id="badge">밝기: 0</div>
                </div>
                <div class="controls">
                    <input type="range" id="slider" min="-100" max="100" step="1" value="0" />
                    <button type="button" id="resetBtn">초기화</button>
                </div>
            </main>
            <script>
                const wrap = document.getElementById('streamWrap');
                const badge = document.getElementById('badge');
                const slider = document.getElementById('slider');
                const resetBtn = document.getElementById('resetBtn');

                let current = 0;
                let dragging = false;
                let dragStartY = 0;
                let dragStartValue = 0;
                let lastSentAt = 0;
                const SENSITIVITY = 0.6;
                const SEND_INTERVAL_MS = 80;

                function clamp(v) {
                    return Math.max(-100, Math.min(100, Math.round(v)));
                }

                function updateUI(value) {
                    current = value;
                    badge.textContent = `밝기: ${value}`;
                    slider.value = value;
                }

                function sendBrightness(value, force) {
                    const now = Date.now();
                    if (!force && now - lastSentAt < SEND_INTERVAL_MS) return;
                    lastSentAt = now;
                    fetch(`/api/camera/brightness?value=${value}`, { method: 'POST' }).catch(() => {});
                }

                async function loadInitial() {
                    try {
                        const res = await fetch('/api/camera/brightness');
                        const data = await res.json();
                        updateUI(clamp(data.brightness || 0));
                    } catch (error) {
                        updateUI(0);
                    }
                }

                wrap.addEventListener('mousedown', (event) => {
                    dragging = true;
                    dragStartY = event.clientY;
                    dragStartValue = current;
                    event.preventDefault();
                });

                window.addEventListener('mousemove', (event) => {
                    if (!dragging) return;
                    const delta = (dragStartY - event.clientY) * SENSITIVITY;
                    const value = clamp(dragStartValue + delta);
                    if (value !== current) {
                        updateUI(value);
                        sendBrightness(value, false);
                    }
                });

                window.addEventListener('mouseup', () => {
                    if (!dragging) return;
                    dragging = false;
                    sendBrightness(current, true);
                });

                wrap.addEventListener('wheel', (event) => {
                    event.preventDefault();
                    const step = event.deltaY > 0 ? -5 : 5;
                    const value = clamp(current + step);
                    updateUI(value);
                    sendBrightness(value, true);
                }, { passive: false });

                slider.addEventListener('input', () => {
                    const value = clamp(Number(slider.value));
                    updateUI(value);
                    sendBrightness(value, false);
                });
                slider.addEventListener('change', () => sendBrightness(current, true));

                resetBtn.addEventListener('click', () => {
                    updateUI(0);
                    sendBrightness(0, true);
                });

                loadInitial();
            </script>
        </body>
    </html>
    """
    return HTMLResponse(content=html)
