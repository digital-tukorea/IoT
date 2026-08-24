#include <Wire.h>
#include <Adafruit_VL53L0X.h>
#include <Servo.h>
#include <Adafruit_NeoPixel.h>
#include <WiFiS3.h>
#include <WiFiUdp.h>
#include <ArduinoMqttClient.h>

// ============================================================
// 🎛️ [주요 파라미터 설정]
// ============================================================
const unsigned long TIME_PUSH_BACK_MS           = 3000;  // 1단계: 뒤 옷 밀기(후진) 및 복귀(전진) 시간 (3초)
const unsigned long TIME_PUSH_FRONT_MS          = 3000;  // 3단계: 앞 옷 밀기(전진) 시간 (3초)
const unsigned long TIME_PUSH_FRONT_RETURN_MS   = 1500;  // 3단계: [1차] 끼임 해제 후진 시간 (1.5초)
const unsigned long TIME_RETURN_TO_TARGET_MS    = 1500;  // 3단계: [2차] 서보 올린 후 타겟 정위치 복귀 후진 시간 (1.5초)

const int TOF_THRESHOLD_DIST       = 500;   // ToF 옷 꺼냄 감지 거리 (mm)
const int PEAK_DELTA_MM            = 25;    // 피크 감지 변화량 임계치 (mm)

const int SPEED_NORMAL             = 80;    // 기본 탐색 속도 (PWM 80)
const int SPEED_PUSH               = 100;   // 옷 밀기 속도
const int SPEED_RETURN             = 100;   // 복귀 속도
const int SPEED_ADJUST             = 100;   // 위치 조정 속도

const int SERVO_ANGLE_UP           = 0;     // 서보 올림 각도
const int SERVO_ANGLE_DOWN         = 150;   // 서보 내림 각도
const int SERVO_DELAY_MS           = 800;   // 서보 동작 대기 시간 (ms)

const unsigned long TIME_ABSENCE_DELAY_MS     = 5000;  // 4단계: 옷 꺼냄 감지 후 복귀 대기 시간 (5초)
const unsigned long TIME_SEARCH_TIMEOUT_MS    = 10000; // 탐색 타임아웃
const unsigned long TIME_HIGHLIGHT_TIMEOUT_MS = 10000; // 조명 미수거 타임아웃


// ============================================================
// ⚙️ [핀 배치 및 네트워크 설정]
// ============================================================
#define PHOTO_PIN    2   
#define MOTOR_ENB    3   
#define MOTOR_IN3    4   
#define MOTOR_IN4    5   
#define SERVO_PIN    9   
#define NEOPIXEL_PIN 7  
#define NUMPIXELS    8   

const char* ssid     = "meka";
const char* password = "84811619";
const char broker[]  = "192.168.137.36";
int        port      = 1883;
const char topic[]   = "rail/target_qr";

WiFiClient wifiClient;
MqttClient mqttClient(wifiClient);

IPAddress receiverIP(192, 168, 137, 255);
const unsigned int localPort = 8888;
WiFiUDP Udp;
char udpBuffer[255];

Servo myServo;
Adafruit_NeoPixel pixels(NUMPIXELS, NEOPIXEL_PIN, NEO_GRB + NEO_KHZ800);
Adafruit_VL53L0X lox = Adafruit_VL53L0X();

#define COLOR_CLOTHES pixels.Color(255, 255, 255)

enum SystemState {
  STATE_IDLE,
  STATE_SEARCH_QR,
  STATE_ADJUST_QR,
  STATE_PUSH_BACK_CLOTHES,
  STATE_MOVE_TO_FRONT_SCAN,
  STATE_PUSH_FRONT_CLOTHES,
  STATE_MONITOR_ABSENCE,
  STATE_RETURN_HOME
};

SystemState currentState = STATE_IDLE;
String targetQR = "";
String scannedQR = "";
String barcodeBuffer = "";

unsigned long stateTimer = 0;
unsigned long idlePingTimer = 0;
unsigned long lastDistLogTimer = 0;
unsigned long lastReturnLogTimer = 0;
unsigned long absenceTimer = 0;

volatile bool isReturningHome = false;
volatile bool homeReached = false;

// ToF 센서 변수
unsigned long lastTofReadTimer = 0;
int cachedDist = 9999;
int errorCount = 0;
int minObservedDist = 9999;

// ============================================================
// 🛠️ [제어 및 로그 함수]
// ============================================================
void sendLog(String logMsg) {
  Serial.print(logMsg);
  if (WiFi.status() == WL_CONNECTED) {
    Udp.beginPacket(receiverIP, localPort);
    Udp.print(logMsg);
    Udp.endPacket();
  }
}

void sendInitLogs() {
  sendLog("\n==================================================\n");
  sendLog("🚀 우노 옷 젖히기 시스템 구동 준비 완료\n");
  sendLog("==================================================\n");
  sendLog("🔄 [상태] -> STATE_IDLE (0)\n");
}

void connectMQTT() {
  if (!mqttClient.connect(broker, port)) {
    sendLog("❌ MQTT 연결 실패\n");
  } else {
    sendLog("✅ MQTT 연결 성공\n");
    mqttClient.subscribe(topic);
  }
}

void setMotor(int speed) {
  if (speed > 0) {
    digitalWrite(MOTOR_IN3, LOW);   
    digitalWrite(MOTOR_IN4, HIGH);  
  } else if (speed < 0) {
    digitalWrite(MOTOR_IN3, HIGH);  
    digitalWrite(MOTOR_IN4, LOW);   
  } else {
    digitalWrite(MOTOR_IN3, LOW);
    digitalWrite(MOTOR_IN4, LOW);
  }
  analogWrite(MOTOR_ENB, abs(speed));
}

void motorBrake() {
  digitalWrite(MOTOR_IN3, HIGH);
  digitalWrite(MOTOR_IN4, HIGH);
  analogWrite(MOTOR_ENB, 255);
  delay(50);
  digitalWrite(MOTOR_IN3, LOW);
  digitalWrite(MOTOR_IN4, LOW);
  analogWrite(MOTOR_ENB, 0);
}

void motorStop() { setMotor(0); }
void motorForward(int speed) { setMotor(speed); }
void motorReverse(int speed) { setMotor(-speed); }

int getToFDistance() {
  if (millis() - lastTofReadTimer < 50) return cachedDist;
  lastTofReadTimer = millis();

  VL53L0X_RangingMeasurementData_t measure;
  lox.rangingTest(&measure, false);

  if (measure.RangeStatus != 4 && measure.RangeMilliMeter > 10 && measure.RangeMilliMeter < 2000) {
    cachedDist = measure.RangeMilliMeter;
    errorCount = 0; 
  } else {
    errorCount++;
    if (errorCount >= 3) cachedDist = 9999;
  }
  return cachedDist;
}

void setLEDsOff() {
  pixels.clear();
  noInterrupts(); 
  pixels.show();
  interrupts();
}

void setLEDsWork(uint32_t color) {
  for (int i = 0; i < NUMPIXELS; i++) pixels.setPixelColor(i, color);
  noInterrupts(); 
  pixels.show();
  interrupts();  
}

void ISR_onHomeReached() {
  homeReached = true;
}

void changeState(SystemState newState) {
  unsigned long elapsed = millis() - stateTimer;
  sendLog("🔄 [상태 전환] " + String(currentState) + " -> " + String(newState) + " (체류: " + String(elapsed) + "ms)\n");
  currentState = newState;
  stateTimer = millis(); 

  if (newState == STATE_MOVE_TO_FRONT_SCAN) {
    minObservedDist = 9999;
  }
}

String formatTargetQR(String input) {
  input.trim();
  input.replace("\r", "");
  input.replace("\n", "");
  input.replace(" ", "");

  int idIndex = input.indexOf("\"id\"");
  if (idIndex == -1) idIndex = input.indexOf("id");

  if (idIndex != -1) {
    int colonIndex = input.indexOf(":", idIndex);
    if (colonIndex != -1) {
      int endIndex = input.indexOf(",", colonIndex);
      if (endIndex == -1) endIndex = input.indexOf("}", colonIndex);
      if (endIndex == -1) endIndex = input.length();

      String val = input.substring(colonIndex + 1, endIndex);
      val.replace("\"", "");
      val.replace("}", "");
      val.replace("{", "");
      val.trim();
      input = val;
    }
  }

  if (input.startsWith("TARGET:")) {
    input = input.substring(7);
    input.trim();
  }
  
  if (input.startsWith("CLOTH_") || input.startsWith("cloth_")) {
    input.toUpperCase();
    return input;
  }
  
  int num = input.toInt();
  if (num > 0 || input == "0") {
    char buf[16];
    sprintf(buf, "CLOTH_%02d", num);
    return String(buf);
  }
  return input;
}

void startSearchSequence(String newTarget) {
  targetQR = formatTargetQR(newTarget);
  while (Serial1.available() > 0) Serial1.read();

  sendLog("🎯 목표 설정: '" + targetQR + "' -> 출발\n");
  delay(500); 

  motorForward(SPEED_NORMAL);
  changeState(STATE_SEARCH_QR);
}

void processScannedQR(String code) {
  code.trim();
  code.replace("\r", "");
  code.replace("\n", "");

  if (code.equalsIgnoreCase("FAIL") || code.equalsIgnoreCase("ERROR")) {
    Serial.println("⚠️ [스캔 실패] 위치 재조정");
    motorReverse(SPEED_ADJUST);
    delay(400);
    motorForward(SPEED_ADJUST);
    delay(400);
    motorForward(SPEED_NORMAL);
    while (Serial1.available() > 0) Serial1.read();
    changeState(STATE_ADJUST_QR);
    return;
  }

  if (code.length() == 0) return;

  String normCode = formatTargetQR(code);
  if (!normCode.startsWith("CLOTH_")) return;

  scannedQR = normCode;
  Serial.print("📷 [스캔 완료]: "); Serial.println(scannedQR);

  if (currentState == STATE_SEARCH_QR || currentState == STATE_ADJUST_QR) {
    if (scannedQR.equalsIgnoreCase(targetQR)) {
      sendLog("🎯 [1차 바코드 일치] 즉시 급제동 후 서보 하강\n");
      motorBrake();
      delay(150);
      myServo.write(SERVO_ANGLE_DOWN);
      delay(SERVO_DELAY_MS); 
      motorReverse(SPEED_PUSH);
      changeState(STATE_PUSH_BACK_CLOTHES);
    } else {
      Serial.print("⏩ 불일치 통과: "); Serial.println(scannedQR);
      motorForward(SPEED_NORMAL);
      changeState(STATE_SEARCH_QR);
    }
  }
}

// ============================================================
// 🚀 [SETUP 및 LOOP]
// ============================================================
void setup() {
  Serial.begin(115200);   
  Serial1.begin(115200);  
  
  Wire.begin();
  Wire.setClock(100000); 
  delay(300);            

  pinMode(MOTOR_IN3, OUTPUT);
  pinMode(MOTOR_IN4, OUTPUT);
  pinMode(MOTOR_ENB, OUTPUT);
  motorStop();

  pinMode(PHOTO_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PHOTO_PIN), ISR_onHomeReached, FALLING);

  bool tofSuccess = false;
  for (int i = 0; i < 3; i++) {
    if (lox.begin(0x29, false, &Wire)) {
      tofSuccess = true;
      break;
    }
    delay(200);
  }

  if (!tofSuccess) {
    Serial.println("❌ ToF 센서 연결 실패!");
  } else {
    lox.configSensor(Adafruit_VL53L0X::VL53L0X_SENSE_LONG_RANGE);
    Serial.println("✅ ToF 센서 장거리 모드 연결 성공!");
  }

  pixels.begin();
  pixels.setBrightness(15); 
  setLEDsOff();

  myServo.attach(SERVO_PIN);
  myServo.write(SERVO_ANGLE_UP);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) delay(500);

  Udp.begin(localPort);
  delay(1000); 
  connectMQTT();

  changeState(STATE_IDLE);
  sendInitLogs(); 
}

void loop() {
  // 1. MQTT 수신
  int mqttSize = mqttClient.parseMessage();
  if (mqttSize) {
    String incoming = "";
    while (mqttClient.available()) incoming += (char)mqttClient.read();
    incoming.trim();
    incoming.replace("\r", "");
    incoming.replace("\n", "");

    if (incoming.length() > 0) {
      startSearchSequence(incoming);
    }
  }

  // 2. 바코드 수신
  while (Serial1.available() > 0) {
    char c = Serial1.read();
    if (c == '\n' || c == '\r') {
      if (barcodeBuffer.length() > 0) {
        processScannedQR(barcodeBuffer);
        barcodeBuffer = "";
      }
    } else {
      barcodeBuffer += c;
    }
  }

  // 3. UDP 수신
  int packetSize = Udp.parsePacket();
  if (packetSize) {
    receiverIP = Udp.remoteIP();
    int len = Udp.read(udpBuffer, 255);
    if (len > 0) {
      udpBuffer[len] = 0;
      String remoteInput = String(udpBuffer);
      remoteInput.trim();
      remoteInput.replace(" ", "");

      if (remoteInput.equalsIgnoreCase("PING")) {
        sendInitLogs();
      } else {
        if (currentState == STATE_IDLE) {
          startSearchSequence(remoteInput);
        } else {
          processScannedQR(remoteInput);
        }
      }
    }
  }

  // 4. 대기 상태 관리
  if (currentState == STATE_IDLE && millis() - idlePingTimer >= 3000) {
    idlePingTimer = millis();
    if (!mqttClient.connected()) connectMQTT();
    sendLog("💤 [UNO] 대기 중 (STATE_IDLE)...\n");
  }

  // 5. 원점 포토 센서 감지 처리
  if (homeReached) {
    homeReached = false;
    if (currentState == STATE_RETURN_HOME || isReturningHome) {
      isReturningHome = false;
      motorBrake();
      setLEDsOff(); 
      myServo.write(SERVO_ANGLE_UP);
      sendLog("🛑 [포토 센서] 원점 도착 완료\n");
      changeState(STATE_IDLE);
    }
  }

  // 6. 메인 FSM 제어
  int currentDist = getToFDistance();

  switch (currentState) {
    case STATE_IDLE:
      break;

    case STATE_SEARCH_QR:
    case STATE_ADJUST_QR:
      if (millis() - stateTimer >= TIME_SEARCH_TIMEOUT_MS) {
        sendLog("⚠️ [탐색 타임아웃] -> 원점 복귀\n");
        setLEDsOff(); 
        myServo.write(SERVO_ANGLE_UP);
        delay(300);
        isReturningHome = true;
        motorReverse(SPEED_RETURN);
        changeState(STATE_RETURN_HOME);
      }
      break;

    case STATE_PUSH_BACK_CLOTHES:
      if (millis() - stateTimer >= TIME_PUSH_BACK_MS) {
        motorBrake();
        delay(150);
        
        sendLog("🛠️ 1단계 복귀: 전진하여 뒤 옷 끼임 해제 중...\n");
        motorForward(SPEED_PUSH);
        delay(TIME_PUSH_BACK_MS);
        
        motorBrake();
        delay(150);
        myServo.write(SERVO_ANGLE_UP);
        delay(SERVO_DELAY_MS);
        
        sendLog("🛠️ 2단계: 서보 올리고 전진하며 2차 피크 탐색 시작\n");
        motorForward(SPEED_PUSH);
        changeState(STATE_MOVE_TO_FRONT_SCAN);
      }
      break;

    case STATE_MOVE_TO_FRONT_SCAN: {
      if (currentDist != 9999 && currentDist < TOF_THRESHOLD_DIST) {
        if (currentDist < minObservedDist) minObservedDist = currentDist;

        if (minObservedDist < 2000 && currentDist >= (minObservedDist + PEAK_DELTA_MM)) {
          sendLog("🎯 [ToF 피크 감지] 옷 중심 통과 확인 -> 즉시 급제동 후 서보 하강\n");
          motorBrake();
          delay(150);
          myServo.write(SERVO_ANGLE_DOWN);
          delay(SERVO_DELAY_MS);

          sendLog("🛠️ 3단계: 서보 내리고 앞 옷 밀기(전진) 시작\n");
          motorForward(SPEED_PUSH);
          changeState(STATE_PUSH_FRONT_CLOTHES);
          break;
        }
      }

      if (millis() - stateTimer >= 3000) {
        sendLog("⚠️ [ToF 타임아웃 3초] 앞 옷 밀기 진입\n");
        motorBrake();
        delay(150);
        myServo.write(SERVO_ANGLE_DOWN);
        delay(SERVO_DELAY_MS);
        motorForward(SPEED_PUSH);
        changeState(STATE_PUSH_FRONT_CLOTHES);
      }
      break;
    }

    // 📌 3단계 앞 옷 밀기 및 2단계 분리 복귀
    case STATE_PUSH_FRONT_CLOTHES:
      if (millis() - stateTimer >= TIME_PUSH_FRONT_MS) {
        motorBrake();
        delay(150);
        
        // 1차 후진: 서보 내린 상태에서 끼임 해제 (1.5초)
        sendLog("🛠️ 3단계 복귀(1/2): 후진하여 앞 옷 끼임 해제 중 (" + String(TIME_PUSH_FRONT_RETURN_MS) + "ms)...\n");
        motorReverse(SPEED_PUSH);
        delay(TIME_PUSH_FRONT_RETURN_MS);
        
        motorBrake();
        delay(150);
        myServo.write(SERVO_ANGLE_UP);
        delay(SERVO_DELAY_MS);

        // 2차 후진: 서보 올린 상태에서 타겟 옷 정위치로 완전 복귀 (1.5초)
        if (TIME_RETURN_TO_TARGET_MS > 0) {
          sendLog("🛠️ 3단계 복귀(2/2): 서보 올리고 타겟 정위치 복귀 후진 중 (" + String(TIME_RETURN_TO_TARGET_MS) + "ms)...\n");
          motorReverse(SPEED_PUSH);
          delay(TIME_RETURN_TO_TARGET_MS);
          motorBrake();
          delay(150);
        }

        sendLog("🎯 [타겟 위치 정렬 완료] 조명 점등 및 옷 꺼냄 감시 시작\n");
        setLEDsWork(COLOR_CLOTHES);
        changeState(STATE_MONITOR_ABSENCE);
      }
      break;

    case STATE_MONITOR_ABSENCE:
      if (millis() - lastDistLogTimer >= 500) {
        lastDistLogTimer = millis();
        sendLog("🔎 [옷 감시 중] 거리: " + String(currentDist) + " mm\n");
      }

      if (currentDist != 9999 && currentDist > TOF_THRESHOLD_DIST) {
        if (absenceTimer == 0) {
          absenceTimer = millis();
          sendLog("⏳ 옷 꺼냄 감지! 5초 대기 후 원점 복귀합니다...\n");
        } 
        else if (millis() - absenceTimer >= TIME_ABSENCE_DELAY_MS) {
          sendLog("🚀 [5초 대기 완료] 원점 복귀 시작\n");
          absenceTimer = 0;
          setLEDsOff(); 
          myServo.write(SERVO_ANGLE_UP);
          delay(400);
          isReturningHome = true;
          motorReverse(SPEED_RETURN);
          changeState(STATE_RETURN_HOME);
        }
      } else {
        if (absenceTimer != 0) {
          absenceTimer = 0;
          sendLog("🔄 옷 재감지됨 (대기 타이머 취소)\n");
        }
      }

      if (millis() - stateTimer >= TIME_HIGHLIGHT_TIMEOUT_MS) {
        sendLog("⚠️ [타임아웃] 자동 원점 복귀\n");
        absenceTimer = 0;
        setLEDsOff(); 
        myServo.write(SERVO_ANGLE_UP);
        delay(400);
        isReturningHome = true;
        motorReverse(SPEED_RETURN);
        changeState(STATE_RETURN_HOME);
      }
      break;

    case STATE_RETURN_HOME:
      if (millis() - lastReturnLogTimer >= 500) {
        lastReturnLogTimer = millis();
        int photoState = digitalRead(PHOTO_PIN);
        sendLog("🔎 [원점 복귀 중] 포토 센서: " + String(photoState == LOW ? "차단" : "열림") + "\n");
      }
      break;
  }

  delay(10);
}