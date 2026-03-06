#include <Arduino.h>
#include <TFT_eSPI.h>
#include <ESP32Servo.h>

/* =========================================================
 * FINAL ROBOT CONTROLLER (Power Up + Reverse Fix)
 * - Pin 16: Camera (360 Servo) -> Time Control
 * - Pin 18: Dumper (180 Servo) -> Angle Control
 * - LCD: Face Display (Big Size)
 * ========================================================= */

// 1. 핀 설정
static const int PIN_CAM_360  = 16;  // 카메라 모터
static const int PIN_DUMP_180 = 18;  // 덤퍼 모터

Servo servoCam;
Servo servoDump;

// =========================================================
// [튜닝 포인트 1] 모터 파워 & 시간
// =========================================================
const int STOP_VAL = 1500; 

// ★ 수정됨: 파워를 최대로 높임 (1000/2000)
const int CW_VAL   = 1000;   // 시계방향 (최고속도)
const int CCW_VAL  = 2000;   // 반시계방향 (최고속도)

// ★ 수정됨: 속도가 빨라진 만큼 시간 조절 (0.01초)
const float SEC_PER_DEG = 0.01; 

// 3. 화면 설정
static TFT_eSPI tft = TFT_eSPI();
static String g_face = "*>w<*";

// 얼굴 그리기 함수
static inline void drawFaceCentered(const String& face) {
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  
  // ★ 수정됨: 글자 크기 3 -> 5 (왕얼굴)
  tft.setTextSize(5); 

  int textW = tft.textWidth(face);
  int textH = tft.fontHeight();
  int x = (tft.width() - textW) / 2;
  int y = (tft.height() - textH) / 2;
  
  if (x < 0) x = 0; if (y < 0) y = 0;
  tft.setCursor(x, y);
  tft.print(face);
}

static inline void setFace(const String& newFace) {
  g_face = newFace;
  drawFaceCentered(g_face);
}

// =========================================================
// [튜닝 포인트 2] 동작 함수 (방향 반전 적용)
// =========================================================

// [카메라] 360도 모터
void moveCamera(int angle) {
  if (angle == 0) return;
  int moveTimeMs = (int)(abs(angle) * SEC_PER_DEG * 1000);
  
  // ★ 수정됨: 방향 반전 (User 요청)
  // angle이 양수(+)일 때 원래는 CW였으나 -> CCW로 바꿈
  if (angle > 0) {
    servoCam.writeMicroseconds(CCW_VAL); 
    Serial.printf("CAM >> CCW(Rev) %d deg (%d ms)\n", angle, moveTimeMs);
  } else {
    servoCam.writeMicroseconds(CW_VAL);
    Serial.printf("CAM >> CW(Rev) %d deg (%d ms)\n", angle, moveTimeMs);
  }
  delay(moveTimeMs);
  servoCam.writeMicroseconds(STOP_VAL); // 정지
}

// [덤퍼] 180도 모터
void moveDumper(int angle) {
  if (angle < 0) angle = 0;
  if (angle > 180) angle = 180;
  servoDump.write(angle);
  Serial.printf("DUMP >> Angle %d\n", angle);
}

// 5. 명령 처리
void handleLine(String line) {
  line.trim();
  if (line.length() == 0) return;

  // 표정: "FACE ^_^"
  if (line.startsWith("FACE ")) {
    setFace(line.substring(5));
    return;
  }

  // 덤퍼: "DUMP 90"
  if (line.startsWith("DUMP ")) {
    int ang = line.substring(5).toInt();
    moveDumper(ang);
    return;
  }

  // 카메라: "-90" (숫자만 오면 카메라)
  int delta = line.toInt();
  if (delta != 0) {
    moveCamera(delta);
  }
}

// 6. 초기화 및 루프
void setup() {
  Serial.begin(115200);

  // 화면 켜기 (S3 백라이트 38번)
  pinMode(TFT_BL, OUTPUT);
  digitalWrite(TFT_BL, HIGH);
  tft.init();
  tft.setRotation(3);
  drawFaceCentered(g_face);

  // 모터 연결
  servoCam.attach(PIN_CAM_360);
  servoCam.writeMicroseconds(STOP_VAL);

  servoDump.attach(PIN_DUMP_180, 500, 2400);
  servoDump.write(0); // 덤퍼 닫기

  Serial.println("READY (PowerUp + Reverse)");
}

void loop() {
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    handleLine(line);
  }
  delay(5);
}
