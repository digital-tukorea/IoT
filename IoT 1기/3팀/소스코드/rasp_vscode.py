import bluepy.btle as btle
import paho.mqtt.client as mqtt
import threading
import json
import time
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)

# ThingsBoard와 EMQX 서버 설정
THINGSBOARD_HOST = 'thingsboard.cloud'  # ThingsBoard 호스트 주소
ACCESS_TOKEN = '7NKUMk2FBdQ7cVAYBuQ7'   # ThingsBoard 장치 액세스 토큰
EMQX_HOST = '34.64.139.72'              # EMQX 서버 주소
EMQX_PORT = 1883                        # EMQX 포트

# ThingsBoard와 EMQX 클라이언트 생성
tb_mqtt_client = mqtt.Client()  # ThingsBoard MQTT 클라이언트
tb_mqtt_client.username_pw_set(ACCESS_TOKEN)  # ThingsBoard에 인증을 위한 액세스 토큰 설정
emqx_mqtt_client = mqtt.Client()  # EMQX MQTT 클라이언트

# MQTT 연결 성공 시 호출되는 콜백 함수 정의 (ThingsBoard)
def on_connect_tb(client, userdata, flags, rc):
    if rc == 0:
        logging.info("Connected to ThingsBoard successfully.")
    else:
        logging.error(f"Failed to connect to ThingsBoard, return code {rc}")

# MQTT 연결 성공 시 호출되는 콜백 함수 정의 (EMQX)
def on_connect_emqx(client, userdata, flags, rc):
    if rc == 0:
        logging.info("Connected to EMQX successfully.")
    else:
        logging.error(f"Failed to connect to EMQX, return code {rc}")

# 콜백 함수 설정
tb_mqtt_client.on_connect = on_connect_tb  # ThingsBoard 연결 시 콜백 설정
emqx_mqtt_client.on_connect = on_connect_emqx  # EMQX 연결 시 콜백 설정

# MQTT 브로커에 연결
tb_mqtt_client.connect(THINGSBOARD_HOST, 1883, 60)  # ThingsBoard에 연결
tb_mqtt_client.loop_start()  # ThingsBoard의 이벤트 루프 시작
emqx_mqtt_client.connect(EMQX_HOST, EMQX_PORT, 60)  # EMQX에 연결
emqx_mqtt_client.loop_start()  # EMQX의 이벤트 루프 시작

# 수집된 데이터를 저장하고 전송하는 클래스 정의
class DataStore:
    def __init__(self):
        self.data = {}  # 수집된 데이터를 저장할 딕셔너리
        self.publish_interval = 1.0  # 데이터 전송 간격 (초 단위)

    # 데이터를 JSON 형식으로 변환하여 ThingsBoard 및 EMQX로 전송하는 함수
    def publish_data(self):
        if self.data:
            json_data = json.dumps(self.data)  # 데이터를 JSON 형식으로 변환
            logging.info(f"Publishing data: {json_data}")
            tb_mqtt_client.publish('v1/devices/me/telemetry', json_data)  # ThingsBoard에 데이터 전송
            emqx_mqtt_client.publish('home/sensors', json_data)  # EMQX에 데이터 전송

# 블루투스 기기에서 데이터를 수신하는 클래스 정의
class ReadDelegate(btle.DefaultDelegate):
    def __init__(self, device_name, data_store):
        super().__init__()
        self.data_buffer = ""  # 블루투스에서 수신된 데이터를 저장할 버퍼
        self.device_name = device_name  # 장치 이름
        self.data_store = data_store  # 수신된 데이터를 저장할 DataStore 객체

    # 블루투스 기기로부터 알림(Notification)을 수신했을 때 호출되는 함수
    def handleNotification(self, cHandle, data):
        try:
            message_part = data.decode("utf-8")  # 수신된 데이터를 UTF-8로 디코딩
            self.data_buffer += message_part  # 디코딩된 데이터를 버퍼에 추가
            if message_part.endswith('\n'):  # 데이터가 끝났는지 확인 (줄바꿈 문자 기준)
                data_dict = json.loads(self.data_buffer.strip())  # 버퍼 내용을 JSON으로 변환
                self.data_store.data.update(data_dict)  # 수신된 데이터를 DataStore에 업데이트
                self.data_buffer = ""  # 버퍼 초기화
        except (UnicodeDecodeError, ValueError) as e:
            logging.error(f"Error processing data from {self.device_name}: {e}")  # 오류 발생 시 출력

# 블루투스 기기와 연결하고 데이터를 처리하는 함수
MAX_RETRIES = 5  # 재연결 시도 최대 횟수
error_logged = set()  # 이미 출력된 오류 메시지를 기록할 집합

def handle_device(address, device_name, data_store):
    retries = 0
    while retries < MAX_RETRIES:
        try:
            p = btle.Peripheral(address)  # 블루투스 기기와 연결
            p.withDelegate(ReadDelegate(device_name, data_store))  # 알림을 처리할 델리게이트 설정
            while True:
                if p.waitForNotifications(1.0):  # 블루투스 알림을 대기 (1초 간격)
                    data_store.publish_data()  # 데이터가 수신되면 전송
        except btle.BTLEDisconnectError as e:
            retries += 1
            if device_name not in error_logged:
                logging.warning(f"Lost connection to {device_name} at {address}. Retrying ({retries}/{MAX_RETRIES})...")
                error_logged.add(device_name)
            time.sleep(10)  # 재연결을 위한 대기
        except Exception as e:
            if device_name not in error_logged:
                logging.error(f"Error with {device_name} at {address}: {e}")
                error_logged.add(device_name)
            break
    if retries >= MAX_RETRIES:
        logging.error(f"Max retries reached for {device_name}. Stopping attempts.")

# DataStore 객체 생성
data_store = DataStore()

# 블루투스 기기 정보 (MAC 주소와 장치 이름)
device_info = [
    ("C8:FD:19:68:81:99", "device1"), 
    ("34:03:DE:4F:54:B2", "device2"), 
    ("60:64:05:92:55:28", "device3")
]

# 각 블루투스 기기를 처리하기 위한 스레드 생성
threads = [threading.Thread(target=handle_device, args=(address, name, data_store)) for address, name in device_info]

# 생성된 스레드 시작
for t in threads:
    t.start()

try:
    for t in threads:
        t.join()  # 모든 스레드가 종료될 때까지 대기
except KeyboardInterrupt:
    # 프로그램 종료 시 MQTT 연결 종료
    tb_mqtt_client.disconnect()
    tb_mqtt_client.loop_stop()
    emqx_mqtt_client.disconnect()
    emqx_mqtt_client.loop_stop()