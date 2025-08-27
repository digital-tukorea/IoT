# IoT
IoT 스마트 융합 프로젝트 과정 파일 저장소입니다.
안녕하세요 테스트 해봅니다。
<미세먼지 센서>

// 메인코드
#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>

// 핀 설정
#define DUST_SENSOR_LED_PIN 26   // 먼지 센서 LED 제어 핀
#define DUST_SENSOR_AOUT_PIN 34  // 먼지 센서 ADC 핀
#define RELAY_PIN 25             // 릴레이 제어 핀

// WiFi 설정
const char* WIFI_SSID = "1team";
const char* WIFI_PASS = "qwer1234";

// MQTT 설정
const char* MQTT_BROKER = "34.64.79.139"; // EMQX 브로커 IP
const int MQTT_PORT = 1883;
const char* MQTT_TOPIC_DUST = "sensor/dust"; // 먼지 농도 전송 토픽
const char* MQTT_TOPIC_FAN  = "/control/fan";   // 팬 제어 토픽

// 센서 관련 상수
const float VCC = 3.3;            // ESP32 전압 (3.3V)
const int ADC_MAX = 4095;         // 12비트 ADC 최대값
const float ACS712_OFFSET = 1.65;   // 0A 기준 전압 (VCC/2)
const float SENSITIVITY = 0.185;    // ACS712 (5A 모델) 감도 (V/A)

WiFiClient espClient;
PubSubClient client(espClient);

// 먼지 농도 임계값 (예시 값)
int dustThreshold = 75;

// 함수 선언
void connectWiFi();
void connectMQTT();
void callback(char* topic, byte* payload, unsigned int length);
int readDustSensor();

void setup() {
  Serial.begin(115200);

  // 핀 모드 설정
  pinMode(DUST_SENSOR_LED_PIN, OUTPUT);
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(DUST_SENSOR_LED_PIN, LOW);
  digitalWrite(RELAY_PIN, LOW);

  // WiFi 연결
  connectWiFi();

  // MQTT 설정
  client.setServer(MQTT_BROKER, MQTT_PORT);
  client.setCallback(callback);
}

void loop() {
  // MQTT 연결 확인 및 재연결
  if (!client.connected()) {
    connectMQTT();
  }
  client.loop();

  // 먼지 센서 데이터 읽기 및 계산
  int dustValue = readDustSensor();
  float voltage = dustValue * (VCC / ADC_MAX);
  float dustDensity = (voltage - 0.9) * 1000 / 5.0;
  if (dustDensity < 0) dustDensity = 0;  // 음수 값 방지

  Serial.print("미세먼지농도: ");
  Serial.print(dustDensity, 2);
  Serial.println(" ug/m3");

  // MQTT로 먼지 농도 데이터 전송
  char dustData[10];
  dtostrf(dustDensity, 6, 2, dustData);
  client.publish(MQTT_TOPIC_DUST, dustData);

  // 먼지 농도에 따라 팬(릴레이) 제어
  if (dustDensity > dustThreshold) {
    digitalWrite(RELAY_PIN, HIGH);
    Serial.println("⚠ 미세먼지 나쁨 - 팬 ON");
  } else {
    digitalWrite(RELAY_PIN, LOW);
    Serial.println("미세먼지 양 정상 - 팬 OFF");
  }

  delay(2000); // 2초 간격
}

// WiFi 연결 함수
void connectWiFi() {
  Serial.print("Wi-Fi 연결 중...");
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWi-Fi 연결 성공! IP 주소: " + WiFi.localIP().toString());
}

// MQTT 브로커 연결 함수
void connectMQTT() {
  while (!client.connected()) {
    Serial.print("MQTT 연결 중...");
    if (client.connect("ESP32_DustSensor")) {
      Serial.println(" 연결 성공!");
      // 팬 제어 토픽 구독
      client.subscribe(MQTT_TOPIC_FAN);
    } else {
      Serial.print(" 실패 (재시도 중...) ");
      delay(2000);
    }
  }
}

// MQTT 메시지 수신 콜백 함수
void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("MQTT 메시지 수신 [");
  Serial.print(topic);
  Serial.print("]: ");
  
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  Serial.println(message);

  // 팬 제어 명령 처리
  if (String(topic) == MQTT_TOPIC_FAN) {
    if (message == "ON") {
      digitalWrite(RELAY_PIN, HIGH);
      Serial.println("팬 ON");
    } else if (message == "OFF") {
      digitalWrite(RELAY_PIN, LOW);
      Serial.println("팬 OFF");
    }
  }
}

// 먼지 센서 데이터 읽기 함수
int readDustSensor() {
  // LED를 켜서 센서 동작 시작
  digitalWrite(DUST_SENSOR_LED_PIN, LOW);
  delayMicroseconds(280);
  int sensorValue = analogRead(DUST_SENSOR_AOUT_PIN);
  delayMicroseconds(40);
  digitalWrite(DUST_SENSOR_LED_PIN, HIGH);
  delayMicroseconds(9680);
  return sensorValue;
}
