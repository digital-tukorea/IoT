# 손동작으로 LED 제어 + 초음파 센서로 문 제어 + EMQ X Broker

import cv2
import mediapipe as mp
import paho.mqtt.client as mqtt_client
from gpiozero import LED
from time import sleep
from gpiozero import DistanceSensor
from gpiozero import Servo
import threading

# MQTT 설정
broker = '192.168.0.36'
port = 1883
topic = "sensor/hand"
client_id = 'qwer_hand'
username = 'hand'  # 여기에 사용자 이름 입력
password = '1q2w3e4r'  # 여기에 비밀번호 입력


#초음파핀 설정
TRIG = 23
ECHO = 24
sensor = DistanceSensor(echo=ECHO, trigger=TRIG)

# 서보모터 핀 설정 (BCM 모드 기준)
servo_pin = 14  # GPIO 14번 핀 사용

# 서보모터 객체 생성
servo = Servo(servo_pin, min_pulse_width=0.5/1000, max_pulse_width=2.5/1000, frame_width=20/1000)

# LED 핀 설정 (예: GPIO 핀 번호 17, 27, 22 사용)
led1 = LED(17)
led2 = LED(27)
led3 = LED(4)

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

def publish(client, distance):
    result = client.publish(topic, distance)
    status = result[0]
    if status == 0:
        print(f"Sent `Distance: {distance:.2f} cm` to topic `{topic}`")
    else:
        print(f"Failed to send message to topic {topic}")


# 각도 설정 함수
def setServoPos(degree):
    # 각도는 180도를 넘을 수 없다.
    if degree > 180:
        degree = 180
    
    # GPIOZero의 Servo 클래스는 -1(0도)에서 1(180도)까지 범위를 가집니다.
    # 따라서, 각도를 -1에서 1 사이의 값으로 변환합니다.
    position = (degree / 180.0) * 2 - 1
    print(f"Degree: {degree} to Position: {position}")
    
    # 서보의 위치를 설정합니다.
    servo.value = position

    # 서보모터가 움직임을 멈춘 후 PWM 신호를 끊어 모터를 중지
    sleep(0.5)  # 모터가 움직일 시간 대기
    servo.detach()  # 모터에 신호를 중단하여 가만히 있게 만듦


# 모든 LED를 끄는 함수
def all_leds_off():
    led1.off()
    led2.off()
    led3.off()

def ultra():
    while True:
        distance = sensor.distance * 100  # 거리를 센티미터로 변환
        print(f"Distance: {distance:.2f} cm")

        # 거리가 10cm 이하일 때 메시지 출력
        if distance <= 10:
            print("문이 열립니다")
            setServoPos(0)

            #servo.value = 0.8 # 서보모터를 오른쪽으로 (130도)
            sleep(10)
            print("문이 닫힙니다")
            setServoPos(120)
            sleep(1)
            #servo.value = -0.5 # 서보모터를 왼쪽으로 (0도)

        sleep(1)

# 손동작 인식 설정
cap = cv2.VideoCapture(0)
mp_drawing = mp.solutions.drawing_utils
mp_hands = mp.solutions.hands

hands = mp_hands.Hands(
    max_num_hands = 1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5)

threading.Thread(target=setServoPos).start()
threading.Thread(target=ultra).start()


try:
    # client = connect_mqtt()
    # client.loop_start()
    while True:
        success, img = cap.read()
        if not success:
            continue
        

        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = hands.process(imgRGB)
        img = cv2.cvtColor(imgRGB, cv2.COLOR_RGB2BGR)

        if results.multi_hand_landmarks:
            for handLms in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(img, handLms, mp_hands.HAND_CONNECTIONS)

                # 손가락 끝(4, 8, 12, 16, 20)과 손가락 중간 관절(6, 10, 14, 18) 비교
                finger_tips = [handLms.landmark[i] for i in [4, 8, 12, 16, 20]]
                finger_dips = [handLms.landmark[i] for i in [3, 7, 11, 15, 19]]

                finger_fold_status = []

                # 엄지손가락은 x축 기준으로 비교
                if finger_tips[0].x > finger_dips[0].x:  # 오른손 기준으로, 왼손이면 방향 반대
                    finger_fold_status.append(True)
                else:
                    finger_fold_status.append(False)

                # 나머지 손가락은 y축 기준으로 비교
                for tip, dip in zip(finger_tips[1:], finger_dips[1:]):
                    if tip.y > dip.y:
                        finger_fold_status.append(False)  # 손가락이 접힘
                    else:
                        finger_fold_status.append(True)  # 손가락이 펴짐

                # 펴진 손가락 개수를 센다
                count = sum(finger_fold_status)

                # 화면에 표시
                cv2.putText(img, str(count), (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 0, 0), 5)

                # LED 제어: 1일 땐 led1, 2일 땐 led2, 3일 땐 led3
                #all_leds_off()
                if count == 1:
                    led1.on()
                elif count == 2:
                    led2.on()
                elif count == 3:
                    led3.on()
                elif count == 4:
                    led3.off()
                elif count == 5:
                    led1.on()
                    led2.on()
                elif count == 0:
                    all_leds_off()
                        

        cv2.imshow("Gotcha", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        
finally:
    all_leds_off()
    cap.release()
    cv2.destroyAllWindows()
    client.loop_stop()
    client.disconnect()