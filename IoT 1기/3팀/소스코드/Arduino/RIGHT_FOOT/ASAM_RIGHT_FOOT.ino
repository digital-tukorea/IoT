//Right
#include <HX711_ADC.h>
#include <SoftwareSerial.h> // 블루투스 통신을 위한 라이브러리

// 핀 설정
const int HX711_dout = 6; // MCU > HX711 dout 핀
const int HX711_sck = 7;  // MCU > HX711 sck 핀

// HX711 객체 생성
HX711_ADC LoadCell(HX711_dout, HX711_sck);

// 블루투스 핀 설정
#define BT_TX 9  // Arduino의 TX 핀 (블루투스 모듈의 RX로 연결)
#define BT_RX 8  // Arduino의 RX 핀 (블루투스 모듈의 TX로 연결)
SoftwareSerial BTSerial(BT_RX, BT_TX); // 블루투스 시리얼 객체

void setup() {
  Serial.begin(9600);      // 시리얼 모니터용 기본 시리얼 통신
  BTSerial.begin(9600);    // 블루투스 통신 시작
  
  // 로드셀 초기화 및 보정 값 설정
  LoadCell.begin();
  LoadCell.start(2000, true);  // 2초 안정화, 영점 조정 수행
  LoadCell.setCalFactor(696.0);  // 보정값 설정 (사용자에 맞게 수정 가능)
  
  Serial.println("로드셀 및 블루투스 통신 준비 완료");
  BTSerial.println("Bluetooth Communication Started");
}

void loop() {
  // 로드셀 데이터가 업데이트되었을 때만 송신
  if (LoadCell.update()) {
    // 무게 계산 및 JSON 형식으로 송신
    float weightInKg = LoadCell.getData() / LoadCell.getCalFactor();
    
    // JSON 형식으로 데이터 전송
    String json = "{\"weight\": ";
    json += String(weightInKg * 25, 3);  // 무게 데이터를 소수점 3자리까지 송신
    json += "}";

    // 시리얼 및 블루투스로 출력
    Serial.println(json);      // 시리얼 모니터로 전송
    BTSerial.println(json);    // 블루투스 모듈로 전송
  }
}
