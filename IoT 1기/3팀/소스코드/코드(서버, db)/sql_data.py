import mysql.connector
import paho.mqtt.client as mqtt
import json
import time
import threading

# MySQL 데이터베이스에 연결
conn = mysql.connector.connect(
    host='34.64.249.216',
    user='root',
    password='iotiot123',
    database='iot3team'
)


# 커서 생성
cursor = conn.cursor()


# 데이터 수신 완료 플래그
data_received = threading.Event()



sql_all = """
INSEERT INTO sensor_all
(latitude, longitude, temperature, humidity, cx, cy, cz, deltaCx, deltaCy, deltaCz, orientation, ppm, load_cell_1, load_cell_2, load_cell_3
 , load_cell_4, timestamp)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,CURRENT_TIMESTAMP + INTERVAL 9 HOUR)
"""


sql_head = """
INSERT INTO sensor_head
(latitude, longitude, temperature, humidity, cx, cy, cz, deltaCx, deltaCy, deltaCz, orientation, timestamp)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP + INTERVAL 9 HOUR)
"""


sql_body = """
INSERT INTO sensor_body
(ppm, timestamp)
VALUES (%s,CURRENT_TIMESTAMP + INTERVAL 9 HOUR)
"""


sql_foor = """
INSERT INTO sensor_data_foot
(load_cell_1, load_cell_2, load_cell_3, load_cell_4, timestamp)
VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP + INTERVAL 9 HOUR)
"""

sql_fatigability = """
INSERT INTO fatigability_data
(fatigability, timestamp)
VALUES (%s, CURRENT_TIMESTAMP + INTERVAL 9 HOUR)
"""

# MQTT 클라이언트 콜백 함수
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    # 특정 토픽을 구독합니다.
    client.subscribe("home/sensors")


def on_message(client, userdata, msg):
    # 메시지 수신 시 출력
    print("Topic: " + msg.topic)
    print("Message: " + str(msg.payload))
    
    
    # JSON 데이터 파싱
    data = json.loads(msg.payload.decode('utf-8'))
    
    # 전체 데이터
    values_all = (
        data["latitude"],
        data["longitude"],
        data["temparature"],
        data["humidity"],
        data["cx"],
        data["cy"],
        data["cz"],
        data["deltaCx"],
        data["deltaCy"],
        data["deltaCz"],
        data["orientation"],
        data["ppm"],
        data["load_cell_1"],
        data["load_cell_2"],
        data["load_cell_3"],
        data["load_cell_4"]
        )
    
    cursor.execute(sql_all, values_all)
    
    # 머리 부분 데이터
    values_head = (
        data["latitude"],
        data["longitude"],
        data["temperature"],
        data["humidity"],
        data["cx"],
        data["cy"],
        data["cz"],
        data["deltaCx"],
        data["deltaCy"],
        deta["deltaCz"],
        data["orientation"]
        )
    
    cursor.execute(sql_head, values_head)
    
    # 몽통 부분 데이터
    values_body = (
       data["ppm"],
        )
    cursor.execute(sql_body, values_body)
    
    # 발 부분 데이터
    values_foot = (
        data["load_cell_1"],
        data["load_cell_2"],
        data["load_cell_3"],
        data["load_cell_4"]
        )
    cursor.execute(sql_foot, values_foot)
    
    # 정확도 부분
    values_fatigability = (
        data["fatigability"],
        )
    
    cursor.execute(sql_fatigability, values_fatigability)

    conn.commit()
    print("Data inserted into MySQL")
    
    # 데이터 수신 완료 플래그 설정
    data_received.set()

# MQTT 클라이언트 생성
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# MQTT 브로커에 연결 (호스트, 포트, 연결 유지 시간)
client.connect("34.64.139.72", 1883, 60)

# MQTT 메시지 수신 대기 (비동기적으로 실행)
client.loop_start()

def periodic_request():
    while True:
        # 데이터 요청
        client.publish("home/sensors/request", "Request data")
        # 메시지가 수신될 때까지 대기
        data_received.wait(timeout=15)  # 15초 대기
        # 데이터 수신 후 플래그 리셋
        data_received.clear()
        # 10초 대기 후 반복
        time.sleep(10)

# 주기적으로 데이터를 요청하는 스레드 시작
thread = threading.Thread(target=periodic_request)
thread.daemon = True
thread.start()

try:
    # 메인 스레드가 종료되지 않도록 유지
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Interrupted by user")
finally:
    # 연결 종료 후 MySQL 연결 닫기
    cursor.close()
    conn.close()
    client.loop_stop()
    client.disconnect()
    
