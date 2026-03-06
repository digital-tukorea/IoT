import time
import cv2
import json
import threading
import requests
import paho.mqtt.client as mqtt
from flask import Flask, Response
from ultralytics import YOLO
from picamera2 import Picamera2

# ================= 설정 =================
MOBIUS_HOST = "192.168.0.5"
MQTT_PORT = 1883
TOPIC_CMD = "Mobius/Robot_Final/command"
TOPIC_STATUS = "Mobius/Robot_Final/status"

app = Flask(__name__)

# 1. YOLO 모델 로드
print("⏳ YOLO 모델 로딩 중...")
try:
    model = YOLO('best.pt') 
    print("✅ YOLO 모델 로드 완료!")
except:
    print("🚨 모델 로드 실패! (best.pt 확인)")
    model = None

# 2. 카메라 설정
try:
    picam2 = Picamera2()
    config = picam2.create_video_configuration(main={"size": (640, 480), "format": "RGB888"})
    picam2.configure(config)
    picam2.start()
    print("✅ 카메라 연결 성공!")
except Exception as e:
    print(f"🚨 카메라 연결 실패: {e}")
    picam2 = None

# 3. MQTT 연결
mqtt_client = mqtt.Client()
try:
    mqtt_client.connect(MOBIUS_HOST, MQTT_PORT, 60)
    mqtt_client.loop_start()
except: pass

last_sent_time = 0

def send_dashboard_status(msg):
    try:
        url = f"http://{MOBIUS_HOST}:7579/{TOPIC_STATUS}"
        headers = {'X-M2M-RI': '12345', 'X-M2M-Origin': 'SbDasq', 'Content-Type': 'application/vnd.onem2m-res+json; ty=4'}
        data = {"m2m:cin": {"con": msg}}
        requests.post(url, headers=headers, json=data, timeout=0.1)
    except: pass

def process_detection(class_name):
    global last_sent_time
    if time.time() - last_sent_time < 2.0: return
    
    command, dash_msg = "", ""
    
    if class_name in ['Battery', 'Scrap']:
        command = "1"; dash_msg = "SORT_BAT"
    elif class_name == 'Can':
        command = "2"; dash_msg = "SORT_CAN"
    elif class_name in ['Paper', 'Plastic']:
        command = "3"; dash_msg = "SORT_ETC"
    
    if command:
        mqtt_client.publish(TOPIC_CMD, command)
        send_dashboard_status(dash_msg)
        print(f"📡 [감지] {class_name} -> {command}")
        last_sent_time = time.time()

def generate_frames():
    if picam2 is None: return
    frame_count = 0
    
    while True:
        try:
            # [단계 1] 이미지 캡처
            frame = picam2.capture_array()
            
            # ★ [수정] 색상 변환 제거 (원본 그대로 사용)
            # frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) -> 삭제함
            
            # [단계 2] YOLO 추론 (3프레임마다 1번)
            if model and (frame_count % 3 == 0):
                results = model(frame, verbose=False, conf=0.5, imgsz=320)
                annotated_frame = results[0].plot()
                
                if results[0].boxes:
                    for box in results[0].boxes:
                        cls_id = int(box.cls[0])
                        process_detection(model.names[cls_id])
            else:
                annotated_frame = frame

            # [단계 3] 상태 표시
            cv2.putText(annotated_frame, "CONVEYOR: ACTIVE", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # [단계 4] 전송
            ret, buffer = cv2.imencode('.jpg', annotated_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if not ret: continue
            
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            
            frame_count += 1
            time.sleep(0.02)

        except Exception as e:
            print(f"에러: {e}")
            time.sleep(1)

@app.route('/stream.mjpg')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    print("🚀 컨베이어 시스템 가동: http://0.0.0.0:8001/stream.mjpg")
    app.run(host='0.0.0.0', port=8001, debug=False, threaded=True)
