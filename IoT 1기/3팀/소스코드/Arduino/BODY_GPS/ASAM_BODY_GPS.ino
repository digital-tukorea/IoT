#include <TinyGPS++.h>
#include <SoftwareSerial.h>

// GPS 모듈의 RX, TX 핀을 아두이노의 4번, 3번 핀에 연결
SoftwareSerial ss(4, 3);
TinyGPSPlus gps;

unsigned long lastSendTime = 0; // 마지막 데이터 전송 시간

void setup() {
  Serial.begin(9600); // 블루투스 모듈과의 통신 속도 (하드웨어 시리얼)
  ss.begin(9600); // GPS 모듈과의 통신 속도 (소프트웨어 시리얼)
  Serial.println("GPS와 Bluetooth 모듈 시작");
}

void loop() {
  // GPS 데이터 읽기
  while (ss.available() > 0) {
    gps.encode(ss.read());
  }

  // 현재 시간
  unsigned long currentMillis = millis();

  // 1초마다 갱신
  if (currentMillis - lastSendTime >= 1000) {
    lastSendTime = currentMillis;
    if (gps.location.isValid()) {
      double latitude = gps.location.lat();
      double longitude = gps.location.lng();

      // JSON 형식으로 데이터 전송
      String json = "{\"latitude\": " + String(latitude, 6) + ", \"longitude\": " + String(longitude, 6) + "}";
      Serial.println(json); // 블루투스로 JSON 데이터 전송
    } else {
      Serial.println("{\"latitude\": 37.7749, \"longitude\": 126.5130}");
    }
  }
}
