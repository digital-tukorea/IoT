"""
mock_upload_server.py
실제 AWS 서버/S3/DB 없이, upload_module.py의 HTTP 요청을 받아
그대로 흉내내서 응답해주는 mock 서버.

사용법:
  pip install flask
  python tools/mock_upload_server.py
  (기본 포트 12345, config.py의 http_port와 맞춰야 함)

받은 이미지는 tools/mock_uploads/ 폴더에 실제로 저장되므로,
카메라가 실제로 뭘 캡처해서 보내는지 눈으로 확인할 수 있다.
"""

import os
import uuid

from flask import Flask, request, jsonify

app = Flask(__name__)

SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mock_uploads")
os.makedirs(SAVE_DIR, exist_ok=True)


@app.route("/api/upload/crop", methods=["POST"])
def upload_crop_image():
    if "image" not in request.files:
        return jsonify({"status": "error", "message": "이미지 파일이 없습니다."}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"status": "error", "message": "선택된 파일이 없습니다."}), 400

    user_id = request.form.get("user_id")
    robot_id = request.form.get("robot_id")
    crop_id = request.form.get("crop_id")
    growth_status = request.form.get("growth_status")
    health_status = request.form.get("health_status")
    zone_id = request.form.get("zone_id")

    if not user_id or not robot_id:
        return jsonify({"status": "error", "message": "필수 파라미터 누락"}), 400

    # 실제로 저장해서 눈으로 확인 가능하게 함
    unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
    save_path = os.path.join(SAVE_DIR, unique_filename)
    file.save(save_path)

    print(f"📥 [Mock 서버] 업로드 수신: user_id={user_id}, robot_id={robot_id}, "
          f"crop_id={crop_id}, growth_status={growth_status}, health_status={health_status}, "
          f"zone_id={zone_id}")
    print(f"   저장 위치: {save_path}")

    # health_status가 disease면 실제 서버처럼 알람 발행 흉내 (콘솔에만 출력)
    if health_status == "disease":
        print(f"🚨 [Mock 서버] disease 감지! 실제라면 여기서 MQTT 알람을 발행했을 것: "
              f"ddalgi/alert/disease/{user_id}")

    fake_image_url = f"http://localhost:12345/mock_uploads/{unique_filename}"
    return jsonify({
        "status": "success",
        "message": "이미지 업로드 및 로깅 완료 (mock)",
        "image_url": fake_image_url,
    }), 200


if __name__ == "__main__":
    print(f"🚀 Mock 업로드 서버 시작 (저장 위치: {SAVE_DIR})")
    app.run(host="0.0.0.0", port=12345)
