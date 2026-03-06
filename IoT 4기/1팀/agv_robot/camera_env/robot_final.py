#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import threading
import sys
import serial
import requests
import json
import cv2
import numpy as np
from dataclasses import dataclass
from flask import Flask, Response
import paho.mqtt.client as mqtt

# 하드웨어 라이브러리 체크
try:
    from mfrc522 import SimpleMFRC522
except:
    SimpleMFRC522 = None

from picamera2 import Picamera2
from ultralytics import YOLO
from rplidar import RPLidar, RPLidarException

# ===========================================================
# [⚙️ 설정 구역]
# ===========================================================
SERVER_IP   = "192.168.0.5"  # 서버 라즈베리파이 IP
MOBIUS_PORT = "7579"
URL_STATUS  = f"http://{SERVER_IP}:{MOBIUS_PORT}/Mobius/Robot_Final/status"

HEADERS = {
    'Accept': 'application/json',
    'X-M2M-RI': '12345',
    'X-M2M-Origin': 'SbDasq',
    'Content-Type': 'application/vnd.onem2m-res+json; ty=4'
}

# ★ 유효한 태그 목록 (데이터 세탁용)
VALID_TAGS = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10"]

# ★ 포트 확정 (ACM0)
ARDUINO_PORT = '/dev/ttyACM0'  
ARDUINO_BAUD = 9600
ESP_PORT     = '/dev/esp32'
ESP_BAUD     = 115200
LIDAR_PORT   = '/dev/ttyUSB0' 

TN_TIME_MS = 1390  
RT_TIME_MS = 900   
IGNORE_DIST_MM = 130  
CAMERA_INDEX = 0      

# ===========================================================
# [Flask 웹서버]
# ===========================================================
app = Flask(__name__)
global_cam = None

def generate_frames():
    while True:
        if global_cam is not None:
            frame = global_cam.read()
            if frame is not None:
                # JPEG 압축 (품질 70%)
                ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        time.sleep(0.05) 

@app.route('/stream.mjpg')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

def run_flask():
    app.run(host='0.0.0.0', port=8000, debug=False, use_reloader=False)

# ===========================================================
# [통신 함수]
# ===========================================================
def _send_debug(url, msg):
    try:
        data = {"m2m:cin": {"con": str(msg)}}
        requests.post(url, headers=HEADERS, json=data, timeout=0.5)
    except: pass

def send_status(msg):
    threading.Thread(target=_send_debug, args=(URL_STATUS, msg)).start()

# ===========================================================
# [클래스 정의]
# ===========================================================
@dataclass
class LidarParams:
    port: str = LIDAR_PORT
    baudrate: int = 115200
    stop_mm: float = 250.0   
    go_mm: float = 300.0     
    stop_hold_s: float = 0.2
    go_hold_s: float = 0.5
    min_quality: int = 10
    reconnect_delay_s: float = 1.0

class LidarGuard:
    def __init__(self, p: LidarParams):
        self.p = p
        self.lock = threading.Lock()
        self.state = "GO"
        self.min_mm = None
        self.target_angle_deg = None
        self._stop_since = None
        self._go_since = None
        self._event = None
        self._stop_flag = False
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        self._stop_flag = True
        if self._thread: self._thread.join(timeout=1.0)

    def get_snapshot(self):
        with self.lock:
            ev = self._event
            self._event = None
            return self.state, self.min_mm, self.target_angle_deg, ev

    def _set_event(self, ev):
        self._event = ev

    def _update_state(self, min_mm):
        now = time.monotonic()
        if min_mm is None:
            self._stop_since = None; self._go_since = None
            return

        if self.state == "GO":
            if min_mm <= self.p.stop_mm:
                if self._stop_since is None: self._stop_since = now
                elif (now - self._stop_since) >= self.p.stop_hold_s:
                    self.state = "STOP"
                    self._stop_since = None; self._go_since = None
                    self._set_event("STOP")
            else:
                self._stop_since = None
        else: 
            if min_mm >= self.p.go_mm:
                if self._go_since is None: self._go_since = now
                elif (now - self._go_since) >= self.p.go_hold_s:
                    self.state = "GO"
                    self._go_since = None; self._stop_since = None
                    self._set_event("GO")
            else:
                self._go_since = None

    def _run(self):
        while not self._stop_flag:
            try:
                lidar = RPLidar(self.p.port, baudrate=self.p.baudrate, timeout=3)
                lidar.start_motor()
                time.sleep(1.0)
                for scan in lidar.iter_scans(max_buf_meas=3000):
                    if self._stop_flag: break
                    min_mm = None; min_angle = None
                    for quality, angle, dist in scan:
                        if quality < self.p.min_quality or dist <= IGNORE_DIST_MM: continue
                        if (min_mm is None) or (dist < min_mm):
                            min_mm = float(dist)
                            min_angle = float(angle)
                    with self.lock:
                        self.min_mm = min_mm
                        self.target_angle_deg = min_angle
                        self._update_state(min_mm)
            except Exception:
                time.sleep(self.p.reconnect_delay_s)
            finally:
                try: lidar.stop(); lidar.stop_motor(); lidar.disconnect()
                except: pass

class CameraStream:
    def __init__(self, size=(640, 480)):
        self.picam2 = Picamera2(camera_num=CAMERA_INDEX)
        # ★ Mode 0 유지 (사용자 확인: 변환 없이 정상)
        config = self.picam2.create_video_configuration(main={"size": size, "format": "RGB888"})
        self.picam2.configure(config)
        self.picam2.start()
        self.frame = None
        self.lock = threading.Lock()
        self.stopped = False
        threading.Thread(target=self._update, daemon=True).start()

    def _update(self):
        while not self.stopped:
            raw = self.picam2.capture_array()
            
            # ★ 색상 변환 없음 (Mode 0)
            with self.lock: self.frame = raw
    
    def read(self):
        with self.lock: return None if self.frame is None else self.frame.copy()

    def stop(self):
        self.stopped = True
        try: self.picam2.stop()
        except: pass

def wrap_to_180(deg): return ((deg + 180.0) % 360.0) - 180.0
def snap_15(deg): return int(round(deg / 15.0) * 15)
def send_esp_cmd(ser, cmd):
    if ser:
        ser.write(f"{cmd}\n".encode())
        print(f"   [ESP TX] {cmd}")

# ===========================================================
# [메인 함수]
# ===========================================================
def main():
    global global_cam
    print("\n🔌 [1/6] 하드웨어 연결 중...")
    
    ser_ard = None
    try:
        ser_ard = serial.Serial(ARDUINO_PORT, ARDUINO_BAUD, timeout=3)
        time.sleep(2)
        # 아두이노 시간 설정
        ser_ard.write(f"TN_TMS,{TN_TIME_MS}\n".encode()); time.sleep(0.1)
        ser_ard.write(f"RT_TMS,{RT_TIME_MS}\n".encode()); time.sleep(0.1)
        ser_ard.flushInput()
        print(f"✅ 아두이노 연결됨 ({ARDUINO_PORT})")
    except:
        print(f"❌ 아두이노 연결 실패 - 포트 확인 필요!")

    ser_esp = None
    try:
        ser_esp = serial.Serial(ESP_PORT, ESP_BAUD, timeout=1)
        print(f"✅ ESP32 연결됨 ({ESP_PORT})")
        send_esp_cmd(ser_esp, "FACE ^_^")
    except:
        print("❌ ESP32 연결 실패")

    reader = None
    if SimpleMFRC522:
        try:
            reader = SimpleMFRC522()
            print("✅ RFID 리더 준비됨")
        except:
            print("❌ RFID 하드웨어 에러")

    # MQTT (셔틀)
    mqtt_client = mqtt.Client()
    try:
        print(f"🌐 [MQTT] 서버({SERVER_IP}) 연결 시도...")
        mqtt_client.connect(SERVER_IP, 1883, 60)
        mqtt_client.loop_start()
        print("✅ MQTT 연결 성공")
    except:
        print("❌ MQTT 연결 실패")
        mqtt_client = None

    print("\n🧠 [2/6] AI 로딩...")
    model = YOLO("yolov8n.pt")
    
    cam = CameraStream()
    global_cam = cam 
    time.sleep(1.0)

    print("\n🌐 [3/6] 영상 서버 시작 (Port 8000)...")
    threading.Thread(target=run_flask, daemon=True).start()

    print("\n📡 [4/6] 라이다 가동...")
    lidar_guard = LidarGuard(LidarParams())
    lidar_guard.start()

    print("\n🚀 [GO] 출발합니다!")
    if ser_ard: ser_ard.write(b"GO\n")
    
    # ★ 출발 시 "START" 상태 전송 (맵에 영향 없음)
    send_status("START") 
    
    current_status = "GO"
    obstacle_processing = False
    last_debug_time = 0

    try:
        while True:
            # 1. 라이다
            state, min_mm, target_angle, event = lidar_guard.get_snapshot()

            if time.time() - last_debug_time > 1.0:
                mm_str = f"{min_mm:.1f}" if min_mm else "None"
                print(f"[LOG] State={state} | Min={mm_str}mm")
                last_debug_time = time.time()

            # 2. 장애물 처리
            if event == "STOP" and not obstacle_processing and current_status == "GO":
                print("\n⛔ [장애물 감지] 로봇 정지!")
                send_status("OBSTACLE") 
                obstacle_processing = True
                
                if ser_ard: ser_ard.write(b"ST\n")
                send_esp_cmd(ser_esp, "FACE o_o")
                
                raw_angle = target_angle if target_angle else 0.0
                delta = wrap_to_180(raw_angle)
                snap = snap_15(delta)
                
                send_esp_cmd(ser_esp, str(snap))
                
                t_end = time.monotonic() + 5.0
                person_detected = False
                while time.monotonic() < t_end:
                    frame = cam.read()
                    if frame is not None:
                        res = model(frame, verbose=False, conf=0.4)
                        if res[0].boxes:
                            for c in res[0].boxes.cls:
                                if model.names[int(c)] == "person":
                                    person_detected = True
                                    break
                    if person_detected: break
                    time.sleep(0.1)

                if person_detected:
                    print("   🙋 사람 발견!")
                    send_status("PERSON")
                    send_esp_cmd(ser_esp, "FACE >_<")
                    time.sleep(3.0)
                else:
                    print("   🤖 사람 아님.")
                    send_esp_cmd(ser_esp, "FACE -_-")
                    time.sleep(2.0)

                send_esp_cmd(ser_esp, str(-snap)) 
                time.sleep(1.0)
                send_esp_cmd(ser_esp, "FACE ^_^")
                
                if ser_ard: ser_ard.write(b"GO\n")
                
                # ★ 장애물 해제 후에는 다시 출발하므로 MOVING
                # (단, 직전에 S태그를 인식했다면 바로 덮어씌워질 수 있음)
                send_status("MOVING") 
                obstacle_processing = False

            # 3. RFID 처리 (데이터 세탁 & 정지 강화)
            if reader and not obstacle_processing:
                try:
                    id, raw_text = reader.read_no_block()
                    if id:
                        # ★ 데이터 세탁: S1~S10만 추출
                        clean_text = raw_text.strip()
                        detected_tag = None
                        for valid in VALID_TAGS:
                            if valid in clean_text:
                                detected_tag = valid
                                break
                        
                        if detected_tag:
                            print(f"\n🏷️ [RFID] 태그 감지: {detected_tag} (원본: {clean_text})")
                            
                            # ★ 깨끗한 태그 전송! (맵 이동)
                            send_status(detected_tag)

                            if detected_tag == "S5":
                                 # ★ S5 즉시 정지
                                 print("\n⛔ [S5 감지] 즉시 정지 명령 전송!!!")
                                 obstacle_processing = True 
                                 
                                 if ser_ard:
                                     ser_ard.write(b"ST\n"); ser_ard.flush()
                                     time.sleep(0.05)
                                     ser_ard.write(b"ST\n"); ser_ard.flush()
                                     time.sleep(2.0) 

                                 print("   🛑 정지 완료 -> 덤핑 시작")
                                 send_status("DUMPING")
                                 
                                 # 1. 회전
                                 if ser_ard:
                                     ser_ard.write(b"TN\n")
                                     time.sleep((TN_TIME_MS / 1000.0) + 1.5)
                                 
                                 # 2. 덤핑 3회
                                 print("   🗑️ 짐 붓기 (3회 털기)")
                                 for i in range(3):
                                     send_esp_cmd(ser_esp, "DUMP 90"); time.sleep(0.5) 
                                     send_esp_cmd(ser_esp, "DUMP 0"); time.sleep(0.5)
                                 
                                 # 3. 셔틀 가동
                                 print("   🚀 [덤핑 완료] 셔틀 가동 명령")
                                 if mqtt_client:
                                     mqtt_client.publish("Mobius/Robot_Final/command", "SHUTTLE_LOAD")
                                 
                                 time.sleep(1.0) 
                                 
                                 # 4. 복귀 및 출발
                                 if ser_ard:
                                     ser_ard.write(b"RT\n")
                                     time.sleep((RT_TIME_MS / 1000.0) + 1.5)
                                     print("   🚀 다시 출발")
                                     ser_ard.write(b"GO\n")
                                 
                                 # 맵 고정을 위해 다시 S5 전송
                                 send_status("S5") 
                                 obstacle_processing = False
                                 time.sleep(3.0) 

                except Exception:
                    pass 

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n🛑 강제 종료")
    finally:
        lidar_guard.stop()
        cam.stop()
        if mqtt_client: mqtt_client.loop_stop(); mqtt_client.disconnect()
        if ser_ard: ser_ard.write(b"ST\n"); ser_ard.close()
        if ser_esp: ser_esp.close()
        print("👋 종료")

if __name__ == "__main__":
    main()
