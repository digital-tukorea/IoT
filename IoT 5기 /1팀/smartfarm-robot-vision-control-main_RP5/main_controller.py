"""
main_controller.py
프로그램 진입점. 각 모듈을 생성하고, 메인 루프에서 순서를 조율한다.

⭐ 이 파일만 4개 모듈(vision/motion/mqtt/upload)의 존재를 전부 알고 있다.
   모듈끼리는 서로를 import하지 않는다 — 항상 이 컨트롤러를 거쳐서만 연결된다.

"""

import os
import time
import queue
import threading
from datetime import datetime

import cv2

from config import CONFIG, CROP_COLOR_PROFILES, resolve_topics, zone_count_to_name
from modules.vision_module import VisionModule
from modules.motion_module import MotionModule
from modules.mqtt_module import MQTTModule
from modules.upload_module import UploadModule
from modules.env_sensor_module import EnvSensorModule


class RobotController:
    def __init__(self, config):
        self.cfg = resolve_topics(config)
        self.is_ai_running = True

        # ★ 구역별 batch_id 일련번호 (프로그램 실행 중 계속 이어짐)
        self._zone_sequence_counters = {}

        os.makedirs(self.cfg["capture_dir"], exist_ok=True)

        if self.cfg.get("vision_enabled", True):
            print("[초기화] 비전 인식 모듈 로드 중...")
            self.vision = VisionModule(self.cfg, CROP_COLOR_PROFILES)
        else:
            print("[초기화] vision_enabled=False -> 비전/카메라 모듈 건너뜀 (주행 전용 모드)")
            self.vision = None

        print("[초기화] 이동 제어 모듈 초기화 중 (USB 시리얼)...")
        self.motion = MotionModule(self.cfg)

        print("[초기화] MQTT 통신 모듈 연결 중...")
        self.comm = MQTTModule(self.cfg)
        self._register_command_handlers()
        self.comm.connect()

        print("[초기화] HTTP 업로드 모듈 준비 중...")
        self.uploader = UploadModule(self.cfg)
        
        print("[초기화] 온습도 센서 모듈 준비 중 (라즈베리파이 직결)...")
        self.env_sensor = EnvSensorModule(self.cfg)

        # ── ★ 비동기 추론용 큐/스레드 ──
        # ★ 카메라 대수만큼은 한 번에 큐에 들어갈 수 있어야 밀리지 않음
        num_cameras = max(1, len(self.cfg.get("camera_indices", [0])))
        self._frame_queue = queue.Queue(maxsize=num_cameras)
        self._result_queue = queue.Queue()
        if self.vision is not None and self.cfg.get("async_inference", True):
            self._inference_thread = threading.Thread(
                target=self._inference_worker, daemon=True
            )
            self._inference_thread.start()
            print("[초기화] 비동기 추론 스레드 시작됨")
        else:
            self._inference_thread = None

    # ── ⭐ 명령 라우팅 ──
    def _register_command_handlers(self):
        # 서버 문서에 AI on/off용 별도 토픽이 없어서, 순찰 명령 토픽 하나로
        # "이동 중계"와 "AI 탐지 on/off"를 함께 처리한다.
        self.comm.on_command(self.cfg["move_command_topic"], self._handle_robot_command)

    def _handle_robot_command(self, payload):
        """
        서버 문서 3-4 규격: {"command": "start_patrol", "target_zone": "zone02", "timestamp": "..."}
        """
        command = payload.get("command", payload.get("action"))

        # 1) 이동 명령은 그대로 motion 모듈에 중계
        self.motion.handle_command(payload)

        # 2) 순찰 시작/정지 여부에 따라 AI 탐지(캡처+YOLO)도 함께 제어
        if command in ("start_patrol", "resume_patrol"):
            self.is_ai_running = True
            print("▶️ 원격 명령 확인: 순찰 + AI 탐지 시작!")
        elif command in ("stop_patrol", "stop"):
            self.is_ai_running = False
            print("⏸️ 원격 명령 확인: 순찰 + AI 탐지 정지!")

    # ── ★ 구역별 batch_id 생성: "{zone_id}_{4자리 일련번호}" ──
    def _make_batch_id(self, zone_id):
        self._zone_sequence_counters[zone_id] = self._zone_sequence_counters.get(zone_id, 0) + 1
        seq = self._zone_sequence_counters[zone_id]
        return f"{zone_id}_{seq:04d}"

    # ── ★ 백그라운드 추론 스레드: 큐에 사진이 들어올 때까지 대기하다가 분석 ──
    def _inference_worker(self):
        while True:
            item = self._frame_queue.get()
            if item is None:   # 종료 신호
                break
            frame, zone_id, now_str = item
            annotated_frame, detections = self.vision.detect(frame, zone_id=zone_id)
            self._result_queue.put((detections, zone_id, now_str))

    # ── 분석이 끝난 결과들을 처리 (HTTP 업로드 + MQTT 메타데이터 발행) ──
    def _process_ready_results(self):
        while True:
            try:
                detections, zone_id, now_str = self._result_queue.get_nowait()
            except queue.Empty:
                return
            
            if not detections:
                print(f"  [{now_str}] zone={zone_id} - 해당 사항 없음 (탐지된 객체 없음)")
                continue   # 아래 for문은 건너뜀

            for detection in detections:
                alert_flags = []
                if detection.disease_detected:
                    alert_flags.append("색상기반병해충")
                if detection.color_change_alert:
                    alert_flags.append("색상급변")
                flag_text = f" [{'/'.join(alert_flags)}]" if alert_flags else ""

                print(f"  [{detection.crop_id}] track={detection.track_id} "
                      f"익음도={detection.ripeness_percent_smoothed}%{flag_text} "
                      f"신뢰도={detection.confidence:.2f}")
                self._dispatch_detection(detection, zone_id)

    # ── 탐지 1건: HTTP(이미지)+MQTT(메타데이터) 분리 전송 ──
    def _dispatch_detection(self, detection, zone_id):
        batch_id = self._make_batch_id(zone_id)

        # ★ 내부 클래스명 -> 서버로 실제 전송할 crop_id로 변환 (예: k_melon -> oriental_melon)
        crop_id = self.cfg.get("crop_id_map", {}).get(detection.crop_id, detection.crop_id)

        # ★ 탐지된 객체(박스) 이미지를 로컬 capture 폴더에도 저장
        if self.cfg.get("save_detected_boxes", True):
            box_filename = f"{batch_id}_{detection.crop_id}.jpg"
            box_dir = os.path.join(self.cfg["capture_dir"], "detected_boxes")
            os.makedirs(box_dir, exist_ok=True)
            box_path = os.path.join(box_dir, box_filename)
            success = cv2.imwrite(box_path, detection.box_bgr)
        if not success:
            print(f"  ❌ 탐지 객체 이미지 저장 실패: {box_path}")

        # 1) HTTP: 이미지 + user_id + robot_id + batch_id 만
        self.uploader.upload(detection.box_bgr, batch_id)

        # 2) MQTT: 나머지 메타데이터 (토픽 = HTTP 엔드포인트 경로와 동일 문자열)
        meta_payload = {
            "user_id": self.cfg["user_id"],
            "robot_id": self.cfg["robot_id"],
            "batch_id": batch_id,
            "crop_id": crop_id,
            "growth_status": detection.growth_status,
            "health_status": detection.health_status,
            "zone_id": zone_id,
        }
        self.comm.publish(self.cfg["crop_meta_topic"], meta_payload)

        # ── 아두이노 텔레메트리 -> 서버 상태 보고 (문서 3-1 규격) ──
    def _poll_and_publish_telemetry(self):
        telemetry = self.motion.read_telemetry()
        if telemetry is None:
            return

        zone_count = int(telemetry.get("zone_count", 0))
        status_payload = {
            "robot_id": self.cfg["robot_id"],
            "current_zone": self.cfg.get("fixed_zone_id", "a1"),   # ★ 고정 zone_id
            "marker_id": f"M{zone_count}",
            # ★ 배터리 상태 확인 기능 자체를 진행하지 않기로 결정 -> MQTT로도 미전송
            "operating_status": telemetry.get("operating_status", "IDLE"),
            "lat": None,   # GPS 미장착
            "lng": None,
        }
        print(f"  [Telemetry] {status_payload}")
        self.comm.publish(self.cfg["telemetry_topic"], status_payload)

    # ── ★ 카메라 열기/닫기 헬퍼 ──
    def _open_cameras(self):
        camera_indices = self.cfg.get("camera_indices", [0])
        caps = [cv2.VideoCapture(idx) for idx in camera_indices]
        opened_flags = [c.isOpened() for c in caps]
        for idx, ok in zip(camera_indices, opened_flags):
            if not ok:
                print(f"⚠️ 카메라 index={idx}를 열 수 없습니다.")
        if not any(opened_flags):
            print("❌ 카메라를 하나도 열 수 없습니다. 연결 상태를 확인하세요.")
            return []
        print(f"📷 [카메라] 순찰 시작 감지 -> 카메라 모듈 활성화 ({sum(opened_flags)}/{len(caps)}대)")
        return caps

    def _release_cameras(self, caps):
        for cap in caps:
            cap.release()
        if caps and self.cfg.get("show_preview", True):
            cv2.destroyAllWindows()

    # ── ★ 온습도 센서 보고 (문서 3-3 handle_env_log 규격)
    def _publish_env_log(self):
        temperature_c, humidity_percent = self.env_sensor.read()

        # 센서가 없거나 이번 판독이 실패했으면(DHT 계열 특성상 흔함) 그냥 건너뜀
        if temperature_c is None:
            print("❌ 온습도 센서를 읽을 수 없습니다. 연결 상태를 확인하세요.")
            return
        else: print(f"  [Env] 온도={temperature_c:.1f}°C, 습도={humidity_percent:.1f}%")
        env_payload = {
            "user_id": self.cfg["user_id"],
            "robot_id": self.cfg["robot_id"],
            "temperature": temperature_c,
            "humidity": humidity_percent,
        }
        print(f"  [Env] {env_payload}")
        self.comm.publish(self.cfg["env_topic"], env_payload)

    # ── 메인 루프 ──
    def run(self):
        if not self.cfg.get("vision_enabled", True):
            self._run_drive_only()
            return

        # ★ 카메라는 프로그램 시작과 동시에 켜지 않는다. "순찰이 시작될 때만"
        # 켜고, 순찰이 아닌 동안은 계속 정지(닫힌) 상태로 유지한다.
        camera_indices = self.cfg.get("camera_indices", [0])
        caps = []

        exit_hint = "'q'를 누르면 종료" if self.cfg.get("show_preview", True) else "Ctrl+C로 종료"
        print(f"🚀 스마트팜 로봇 제어 시작... (대기 중 - 순찰 시작 시 카메라 활성화, {exit_hint})")

        # ★ [캡처 트리거 변경] 아두이노가 마커에서 자연스럽게 멈추는 순간
        # (원래 구역 카운트용으로 쓰던 그 정지)을 감지해서 캡처 트리거로 재사용한다. 
        # STATUS가 "PAUSED"로 바뀌는 그 전환 순간(엣지)에만 한 번 캡처한다.
        last_operating_status = None
        last_telemetry_poll_time = 0
        last_telemetry_republish_time = 0
        last_heartbeat_time = 0
        last_env_report_time = 0
        annotated_frame = None

        try:
            while True:
                # ── ★ 카메라 모듈: 순찰 상태(is_ai_running)에 맞춰 켜고 끄기 ──
                if self.is_ai_running and not caps:
                    caps = self._open_cameras()
                elif not self.is_ai_running and caps:
                    self._release_cameras(caps)
                    caps = []
                    annotated_frame = None
                    print("📷 [카메라] 순찰 정지 감지 -> 카메라 모듈 비활성화")

                now = time.time()

                # 🛡️ 안전 타임아웃용 하트비트 (카메라 상태와 무관하게 항상 동작)
                if now - last_heartbeat_time >= self.cfg["heartbeat_interval_sec"]:
                    last_heartbeat_time = now
                    self.motion.send_heartbeat()

                if now - last_telemetry_poll_time >= self.cfg["telemetry_poll_interval_sec"]:
                    last_telemetry_poll_time = now
                    self.motion.read_telemetry()

                if now - last_telemetry_republish_time >= self.cfg["telemetry_republish_interval_sec"]:
                    last_telemetry_republish_time = now
                    self._poll_and_publish_telemetry()

                # ★ 온습도 센서 보고 (카메라 상태와 무관하게 항상 동작)
                if now - last_env_report_time >= self.cfg["env_report_interval_sec"]:
                    last_env_report_time = now
                    self._publish_env_log()

                # ★ 백그라운드에서 분석 끝난 결과가 있으면 처리 (메인 루프를 안 막음)
                self._process_ready_results()

                if not caps:
                    # 카메라가 꺼진 상태(순찰 중이 아님) - CPU 낭비 방지용 짧은 대기
                    time.sleep(0.1)
                    continue

                # ── 실시간 미리보기는 첫 번째로 연결된 카메라 화면만 사용 ──
                preview_frame = None
                for cap in caps:
                    if not cap.isOpened():
                        continue
                    success, frame = cap.read()
                    if success:
                        preview_frame = frame
                        break

                if preview_frame is None:
                    # 카메라가 열려있다고 판단했는데 이번 프레임만 못 읽은 경우 - 다음 루프에서 재시도
                    continue

                # ★ [zone_id 체계 변경] GPS/마커 카운트 기반 
                zone_name = self.cfg.get("fixed_zone_id", "a1")

                # ★ show_preview=False(헤드리스)면 화면 표시 관련 연산 자체를 건너뛴다.
                if self.cfg.get("show_preview", True):
                    display_frame = annotated_frame if annotated_frame is not None else preview_frame
                    status_text = "RUNNING" if self.is_ai_running else "PAUSED (원격 정지됨)"
                    cv2.putText(display_frame, f"Status: {status_text} | Zone: {zone_name}",
                                (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                                (0, 255, 0) if self.is_ai_running else (0, 165, 255), 2)
                    cv2.imshow("Smart Farm AI Camera", display_frame)

                # ══════════════════════════════════════════════════════════
                # ▼▼▼▼▼ [마커 기반 캡처 트리거] ▼▼▼▼▼
                # ★ 아두이노가 마커에서 자연스럽게 멈추는 순간(원래 구역
                # 카운트용으로 쓰던 정지)을 그대로 캡처 트리거로 재사용한다.
                # STATUS가 "PAUSED"로 "바뀌는 그 전환 순간"에만 한 번 캡처한다
                # (계속 PAUSED 상태인 동안 매 루프마다 중복 캡처되지 않도록
                # 엣지 감지를 한다). Pi가 별도로 정지/재개 명령을 보낼 필요가
                # 없다 - 아두이노가 스스로 멈췄다가 스스로 다시 출발한다.
                current_status = None
                latest_telemetry = self.motion.get_latest_telemetry()
                if latest_telemetry is not None:
                    current_status = latest_telemetry.get("operating_status")

                just_entered_paused = (
                    current_status == "PAUSED" and last_operating_status != "PAUSED"
                )
                last_operating_status = current_status

                if self.is_ai_running and just_entered_paused:
                    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                    zone_id = zone_name   # ★ 카메라 대수와 무관하게 구역 하나로 공유

                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 마커 정지 감지 -> 캡처 시작 "
                          f"(zone={zone_id}, 카메라 {sum(c.isOpened() for c in caps)}대)")

                    # 흔들림이 완전히 가라앉을 때까지 아주 잠깐 대기 후 촬영
                    time.sleep(self.cfg["capture_pause_stabilize_sec"])

                    # ★ 연결된 카메라 전부에서 각각 프레임을 읽어, 전부 같은 zone_id로 큐에 넣는다.
                    #   (분석 스레드/디스패치 로직은 "어느 카메라에서 왔는지" 전혀 신경 안 씀 -
                    #    큐 아이템 구조 자체를 바꿀 필요가 없다.)
                    queued_count = 0
                    for cam_idx, cap in zip(camera_indices, caps):
                        if not cap.isOpened():
                            continue
                        success, frame = cap.read()
                        if not success:
                            print(f"  ⚠️ 카메라 index={cam_idx} 프레임을 읽어오지 못해 건너뜀")
                            continue
                        try:
                            self._frame_queue.put_nowait((frame, zone_id, now_str))
                            queued_count += 1
                        except queue.Full:
                            print(f"  [경고] 이전 분석이 아직 진행 중이라 카메라 index={cam_idx} "
                                  f"캡처는 건너뜁니다.")

                    if queued_count == 0:
                        print("❌ 이번 캡처에서 큐에 넣은 프레임이 하나도 없습니다.")
                    # 정지/재개 명령을 Pi가 보낼 필요 없음 - 아두이노가 자체적으로
                    # 5초 정차 후 알아서 재출발한다.
                # ▲▲▲▲▲ [마커 기반 캡처 트리거] 끝 ▲▲▲▲▲
                # ══════════════════════════════════════════════════════════

                if self.cfg.get("show_preview", True) and cv2.waitKey(1) & 0xFF == ord("q"):
                    break

        except KeyboardInterrupt:
            # ★ 헤드리스(show_preview=False) 상태에서는 'q' 키를 누를 수 없으므로,
            #   Ctrl+C(또는 systemd stop이 보내는 SIGTERM->KeyboardInterrupt)로 종료한다.
            print("\n[종료 요청] Ctrl+C 감지, 안전하게 종료합니다...")

        self._release_cameras(caps)
        self._shutdown()

    # ── ★ 주행 전용 모드: 카메라/YOLO 없이, 이동 명령 중계 + 텔레메트리만 처리 ──
    def _run_drive_only(self):
        print("🚗 [주행 전용 모드] 카메라/YOLO 없이 이동 명령만 처리합니다. (종료: Ctrl+C)")
        last_heartbeat_time = 0
        last_telemetry_poll_time = 0
        last_telemetry_republish_time = 0

        try:
            while True:
                now = time.time()
                if now - last_heartbeat_time >= self.cfg["heartbeat_interval_sec"]:
                    last_heartbeat_time = now
                    self.motion.send_heartbeat()
                if now - last_telemetry_poll_time >= self.cfg["telemetry_poll_interval_sec"]:
                    last_telemetry_poll_time = now
                    self.motion.read_telemetry()
                if now - last_telemetry_republish_time >= self.cfg["telemetry_republish_interval_sec"]:
                    last_telemetry_republish_time = now
                    self._poll_and_publish_telemetry()
                time.sleep(0.05)
        except KeyboardInterrupt:
            print("\n[종료 요청] Ctrl+C 감지, 안전하게 종료합니다...")
        finally:
            self._shutdown()

    def _shutdown(self):
        # 백그라운드 추론 스레드 종료 신호 + 마지막 결과 처리
        if self._inference_thread is not None: 
            self._frame_queue.put(None)
            self._inference_thread.join(timeout=5)
        self._process_ready_results()

        self.motion.close()
        self.comm.disconnect()


if __name__ == "__main__":
    controller = RobotController(CONFIG)
    controller.run()
