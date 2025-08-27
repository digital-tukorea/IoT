// MQ-135 가스 센서 핀
const int mq135Pin = A0;

void setup() {
  // 시리얼 통신 초기화 (블루투스 모듈과 통신)
  Serial.begin(9600);

  Serial.println("Bluetooth Communication Started with Gas Sensor");
}

void loop() {
  // MQ-135 가스 센서로부터 아날로그 값 읽기
  int gasSensorValue = analogRead(mq135Pin);

  // JSON 형식으로 가스 센서 데이터 변환
  String json = "{\"ppm\":";
  json += String(gasSensorValue);
  json += "}";

  // JSON 데이터를 시리얼 모니터와 블루투스로 전송
  Serial.println(json);

  // 1초 대기
  delay(1000);
}
