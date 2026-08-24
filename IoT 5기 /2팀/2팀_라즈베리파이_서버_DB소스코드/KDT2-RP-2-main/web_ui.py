"""홈 화면 라우터

브라우저로 서버에 접속했을 때 보이는 간단한 상태 페이지( / )를
제공한다. 옷장 DB 내용을 표로 보여주고, id별로 수동 업로드/레일 전송
버튼을 둔다. 실시간 카메라 화면은 routes_camera.py의
/video_feed/view가 담당한다.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from database import fetch_closet_inventory

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    inventory = fetch_closet_inventory()

    rows_html = []
    if inventory:
        for item in inventory:
            image_id = item.get('id', '')
            file_path = item.get('filepath', '')
            image_name = Path(str(file_path)).name if file_path else ""
            image_url = f"/images/download/{image_name}" if image_name else ""
            preview_html = (
                f"<div class='preview-card'>"
                f"<button type='button' class='send-btn' onclick='sendSlot({image_id})'>📤</button>"
                f"<img src=\"{image_url}\" alt=\"{image_name}\" class=\"preview\" />"
                f"</div>"
            ) if image_url else ""
            rows_html.append(
                "<tr>"
                f"<td>{image_id}</td>"
                f"<td>{preview_html}</td>"
                f"<td>{file_path}</td>"
                f"<td>{item.get('description', '')}</td>"
                f"<td>{item.get('created_at', '')}</td>"
                "</tr>"
            )
        db_section = """
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Preview</th>
                        <th>File Path</th>
                        <th>Description</th>
                        <th>Created At</th>
                    </tr>
                </thead>
                <tbody>
        """ + "".join(rows_html) + """
                </tbody>
            </table>
        """
    else:
        db_section = "<div class='empty-state'>DB에 아직 저장된 항목이 없습니다.</div>"

    html = """
    <!doctype html>
    <html lang="ko">
        <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>Smart Closet Backend</title>
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
                    padding: 32px;
                    border-radius: 16px;
                    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
                    max-width: 640px;
                    width: calc(100% - 32px);
                }
                .section {
                    margin-top: 24px;
                    padding-top: 20px;
                    border-top: 1px solid #e5e7eb;
                }
                h1 { margin-top: 0; }
                .links a {
                    display: inline-block;
                    margin-right: 12px;
                    margin-bottom: 12px;
                    padding: 10px 14px;
                    border-radius: 999px;
                    background: #111827;
                    color: white;
                    text-decoration: none;
                }
                .links a.secondary { background: #2563eb; }
                code { background: #f3f4f6; padding: 2px 6px; border-radius: 6px; }
                form {
                    display: grid;
                    gap: 10px;
                    margin-top: 16px;
                }
                form label {
                    display: block;
                    font-weight: bold;
                    margin-bottom: 4px;
                }
                form select,
                form input[type=file],
                form button {
                    width: 100%;
                    padding: 10px;
                    border-radius: 10px;
                    border: 1px solid #d1d5db;
                    font-size: 14px;
                }
                form button {
                    background: #111827;
                    color: white;
                    border: none;
                    cursor: pointer;
                }
                form button:hover {
                    background: #1f2937;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 12px;
                    font-size: 14px;
                }
                th, td {
                    text-align: left;
                    border-bottom: 1px solid #e5e7eb;
                    padding: 10px 8px;
                    vertical-align: top;
                    word-break: break-word;
                }
                th {
                    background: #f9fafb;
                }
                .empty-state {
                    margin-top: 12px;
                    padding: 14px;
                    border-radius: 12px;
                    background: #f9fafb;
                    color: #6b7280;
                }
                .preview {
                    max-width: 120px;
                    max-height: 90px;
                    object-fit: contain;
                    border: 1px solid #e5e7eb;
                    border-radius: 8px;
                    background: #fff;
                }
                .preview-card {
                    display: inline-flex;
                    flex-direction: column;
                    gap: 8px;
                    align-items: flex-start;
                }
                .send-btn {
                    border: none;
                    border-radius: 999px;
                    background: #2563eb;
                    color: white;
                    padding: 6px 10px;
                    cursor: pointer;
                    font-size: 12px;
                }
            </style>
            <script>
                async function sendSlot(imageId) {
                    try {
                        const response = await fetch(`/api/send_id/${imageId}`, { method: 'POST' });
                        const data = await response.json();
                        if (response.ok) {
                            alert(`전송 완료: id=${data.id}`);
                        } else {
                            alert(`전송 실패: ${data.detail || 'unknown error'}`);
                        }
                    } catch (error) {
                        alert('전송 실패: MQTT 브로커 연결 오류');
                    }
                }
            </script>
        </head>
        <body>
            <main class="card">
                <h1>Smart Closet Backend</h1>
                <p>서버가 정상 동작 중입니다.</p>
                <p>확인할 주소:</p>
                <div class="links">
                    <a href="/docs">API Docs</a>
                    <a class="secondary" href="/video_feed/view">MJPEG Stream (조도 조절)</a>
                    <a href="/video_feed">MJPEG Raw</a>
                </div>
                <div class="section">
                    <h2>DB 상태</h2>
                    <p>추천 API: <code>/api/recommend</code></p>
                    <p>파일 업로드: id 1~10에 해당하는 JPG/PNG 이미지를 업로드하면 자동으로 저장 및 DB에 반영됩니다.</p>
                    <form id="upload-form" action="/api/upload/1" method="post" enctype="multipart/form-data">
                        <label for="upload-id">ID</label>
                        <select id="upload-id" name="id" onchange="document.getElementById('upload-form').action='/api/upload/'+this.value;">
                            <option value="1">1</option>
                            <option value="2">2</option>
                            <option value="3">3</option>
                            <option value="4">4</option>
                            <option value="5">5</option>
                            <option value="6">6</option>
                            <option value="7">7</option>
                            <option value="8">8</option>
                            <option value="9">9</option>
                            <option value="10">10</option>
                        </select>
                        <input type="file" name="file" accept="image/jpeg,image/png" required />
                        <button type="submit">업로드</button>
                    </form>
                    __DB_SECTION__
                </div>
            </main>
        </body>
    </html>
    """
    return HTMLResponse(content=html.replace("__DB_SECTION__", db_section))
