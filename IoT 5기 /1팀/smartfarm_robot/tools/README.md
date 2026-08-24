# tools/

개발/테스트용 독립 스크립트 모음. main_controller.py는 이 폴더의 어떤 파일도
자동으로 불러오지 않는다 (전부 따로 실행하는 보조 도구).

- send_test_command.py : MQTT로 이동 명령을 수동으로 보내보는 테스트 도구
- mock_arduino.py       : 실제 아두이노 없이 시리얼 응답을 흉내내는 테스트용
- mock_upload_server.py : 실제 서버 없이 HTTP 업로드를 받아주는 테스트용 서버
- test_vision_module.py : 카메라/로봇 없이 이미지 한 장으로 vision_module만 테스트
