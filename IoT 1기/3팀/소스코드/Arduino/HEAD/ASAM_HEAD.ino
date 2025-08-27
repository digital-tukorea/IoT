#include <DHT.h>
#include <Wire.h> // I2C 통신을 위해 필요
#include <SparkFun_MMA8452Q.h>
#include <SoftwareSerial.h> // 블루투스 통신을 위한 라이브러리

// DHT22 설정
#define DHTPIN 4         // AM2302 센서가 연결된 디지털 핀 번호
#define DHTTYPE DHT22    // DHT 22 (AM2302)
DHT dht(DHTPIN, DHTTYPE);  // DHT 객체 생성

// MMA8452Q 가속도계 설정
MMA8452Q acelerometro(0x1C); // I2C 주소는 기본값 (0x1C)

// 블루투스 핀 설정
#define BT_TX 9  // Arduino의 TX 핀 (블루투스 모듈의 RX로 연결)
#define BT_RX 8  // Arduino의 RX 핀 (블루투스 모듈의 TX로 연결)
SoftwareSerial BTSerial(BT_RX, BT_TX); // 블루투스 시리얼 객체

// 타이머 설정
unsigned long previousMillisDHT = 0; // DHT 이전 시간 저장 변수
unsigned long previousMillisAccel = 0; // 가속도계 이전 시간 저장 변수
const long intervalDHT = 1000; // DHT 간격 1초
const long intervalAccel = 1000; // 가속도계 간격 1초

// 이전 가속도 값 저장 변수
float prevCx = 0, prevCy = 0, prevCz = 0;

void setup() {
  Serial.begin(9600);      // 하드웨어 시리얼 통신 초기화
  BTSerial.begin(9600);    // 블루투스 시리얼 통신 초기화
  dht.begin();             // DHT 센서 초기화
  Wire.begin();            // I2C 통신 초기화
  acelerometro.init();     // 가속도계 초기화
  Serial.println("Communication Started with AM2302 and MMA8452Q Sensors");
  BTSerial.println("Bluetooth Communication Started");
}

void loop() {
  unsigned long currentMillis = millis();
  
  // DHT22 센서 읽기 및 출력
  if (currentMillis - previousMillisDHT >= intervalDHT) {
    previousMillisDHT = currentMillis;

    // 온도와 습도 읽기
    float h = dht.readHumidity();        // 습도 읽기
    float t = dht.readTemperature();     // 온도 읽기 (섭씨 기준)

    // 읽은 값의 유효성 검사
    if (isnan(h) || isnan(t)) {
      Serial.println("Failed to read from DHT sensor!");
      BTSerial.println("Failed to read from DHT sensor!"); // 블루투스로 전송
    } else {
      // JSON 형식으로 데이터 합치기
      String json = "{\"temperature\":";
      json += String(t);
      json += ",\"humidity\":";
      json += String(h);
      json += "}";

      // 시리얼로 출력 및 블루투스 전송
      Serial.println(json);
      BTSerial.println(json); // 블루투스로 데이터 전송
    }
  }

  // 가속도계 데이터 읽기 및 출력
  if (currentMillis - previousMillisAccel >= intervalAccel) {
    previousMillisAccel = currentMillis;

    // 가속도계 데이터 읽기
    if (acelerometro.available()) {
      acelerometro.read();
      String accelData = printCalculatedAccels() + printOrientation();
      Serial.println(accelData);  // 시리얼 모니터 출력
      BTSerial.println(accelData); // 블루투스 모듈로 데이터 전송
    }
  }
}

String printCalculatedAccels() { 
  // 가속도 변화율 계산
  float deltaCx = acelerometro.cx - prevCx;
  float deltaCy = acelerometro.cy - prevCy;
  float deltaCz = acelerometro.cz - prevCz;

  // 이전 가속도 값을 현재 값으로 갱신
  prevCx = acelerometro.cx;
  prevCy = acelerometro.cy;
  prevCz = acelerometro.cz;

  // JSON 형식으로 가속도 데이터 출력
  String accelData = "{\"cx\":";
  accelData += String(acelerometro.cx, 3);
  accelData += ",\"cy\":";
  accelData += String(acelerometro.cy, 3);
  accelData += ",\"cz\":";
  accelData += String(acelerometro.cz, 3);
  
  // 가속도 변화율 데이터 추가
  accelData += ",\"deltaCx\":";
  accelData += String(deltaCx, 3);
  accelData += ",\"deltaCy\":";
  accelData += String(deltaCy, 3);
  accelData += ",\"deltaCz\":";
  accelData += String(deltaCz, 3);
  
  accelData += ",";
  return accelData;
}

String printOrientation() {
  String orientation = "\"orientation\":\"";
  switch (acelerometro.readPL()) {
    case PORTRAIT_U: orientation += "Back"; break;
    case PORTRAIT_D: orientation += "Front"; break;
    case LANDSCAPE_R: orientation += "Right"; break;
    case LANDSCAPE_L: orientation += "Left"; break;
    case LOCKOUT: orientation += "Flat"; break;
  }
  orientation += "\"}";
  return orientation;
}
