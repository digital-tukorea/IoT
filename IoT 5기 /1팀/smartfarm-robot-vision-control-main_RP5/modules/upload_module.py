"""
upload_module.py
서버의 /api/upload/crop REST API 호출을 캡슐화한다.

"""

from datetime import datetime

import cv2
import requests


class UploadModule:
    def __init__(self, config):
        self.config = config

    def upload(self, box_bgr, batch_id):
        """
        박스 이미지(numpy array, BGR)를 서버에 업로드한다.
        ★ 이미지 외에는 user_id/robot_id/batch_id만 같이 보낸다
        (crop_id/growth_status/health_status/zone_id는 MQTT 쪽 책임).
        반환값: (성공 여부: bool, response 객체 또는 None)
        """
        success, encoded = cv2.imencode(".jpg", box_bgr)
        if not success:
            print("  [HTTP 에러] 이미지 인코딩 실패, 업로드 스킵")
            return False, None

        img_bytes = encoded.tobytes()
        filename = f"{batch_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"

        try:
            files = {"image": (filename, img_bytes, "image/jpeg")}
            data = {
                "user_id": self.config["user_id"],
                "robot_id": self.config["robot_id"],
                "batch_id": batch_id,   # ★ MQTT로 보낸 메타데이터와 매칭하는 키
            }
            response = requests.post(
                self.config["http_upload_url"], files=files, data=data, timeout=5
            )

            if response.status_code in (200, 201):
                print(f"  [HTTP 성공] 이미지 업로드 완료 ({response.status_code}) batch_id={batch_id}")
                return True, response
            else:
                print(f"  [HTTP 실패] 응답 코드: {response.status_code} | 본문: {response.text}")
                return False, response

        except requests.exceptions.ConnectTimeout:
            print("  [HTTP 에러] 연결 타임아웃: 서버 IP/포트, 네트워크 상태를 확인하세요.")
            return False, None
        except Exception as e:
            print(f"  [HTTP 에러] 이미지 전송 실패: {e}")
            return False, None
