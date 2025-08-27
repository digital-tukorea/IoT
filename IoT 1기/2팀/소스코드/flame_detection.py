# 화재 감지 + 경보음

from gpiozero import InputDevice
from gpiozero import PWMOutputDevice
import time
from time import sleep
import paho.mqtt.client as mqtt_client

# MQTT 설정
broker = '192.168.0.36'
port = 1883
topic = "sensor/fire"
client_id = 'qwer_fire'
username = 'fire'  # 여기에 사용자 이름 입력
password = '1q2w3e4r'  # 여기에 비밀번호 입력


# FLAME_SENSOR_PIN은 불꽃 감지 센서가 연결된 GPIO 핀 번호입니다.
FLAME_SENSOR_PIN = 22  # 이 핀 번호는 예시입니다. 실제로 연결된 핀 번호로 변경해야 합니다.
buzzer = PWMOutputDevice(2, frequency=600)

def connect_mqtt():
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("MQTT Broker 연결 성공!")
        else:
            print("연결 실패, 코드로 돌아갑니다. %d\n", rc)
    
    client = mqtt_client.Client(client_id=client_id)  # 기본 API 사용
    client.username_pw_set(username, password)  # 사용자 이름과 비밀번호 설정
    client.on_connect = on_connect
    client.connect(broker, port)
    return client

def publish(client, flame_sensor_state):
    result = client.publish(topic, flame_sensor_state)
    status = result[0]
    if status == 0:
        print(f"Published: {flame_sensor_state}")
    else:
        print(f"Failed to send message to topic {topic}")


def main():
    # 불꽃 감지 센서를 InputDevice로 설정합니다.
    flame_sensor = InputDevice(FLAME_SENSOR_PIN)
    client = connect_mqtt()
    client.loop_start()

    try:
        while True:
            # 현재 시간을 가져옵니다.
            now = time.localtime()
            # 시간을 포맷에 맞춰 문자열로 변환합니다.
            timestamp = ("%04d-%02d-%02d %02d:%02d:%02d" %
                        (now.tm_year, now.tm_mon, now.tm_mday,  # 연도, 월, 일
                        now.tm_hour, now.tm_min, now.tm_sec))  # 시, 분, 초
            
            if flame_sensor.is_active:
                # 센서가 '1'이면 불꽃이 감지되지 않은 상태로 "안전"을 출력합니다.
                print(timestamp, "안전")
                publish(client, "안전")
                sleep(10)
            else:
                # 센서가 '0'이면 불꽃이 감지된 상태로 "화재 경보"를 출력합니다.
                print(timestamp, "화재 경보")
                publish(client, "화재 경보")
                # 부저 시작 (Duty cycle 50%)
                buzzer.value = 0.7
                sleep(10)
                # 부저 멈춤
                buzzer.off()
                sleep(1)  
            
            

    except KeyboardInterrupt:
        print("프로그램 종료 (Ctrl+C)")

    finally:
        print("스크립트 종료")
        client.loop_stop()
        client.disconnect()

if __name__ == '__main__':
    main()