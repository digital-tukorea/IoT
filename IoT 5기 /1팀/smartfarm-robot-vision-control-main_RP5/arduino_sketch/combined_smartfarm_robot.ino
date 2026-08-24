/*
  combined_smartfarm_robot.ino

  ★★★ 오늘 변경: GPIO(D3/D4, SoftwareSerial) 대신 USB 케이블로 아두이노를
  라즈베리파이에 직접 연결하는 방식으로 되돌렸다. 라즈베리파이의 USB 포트가
  전원 공급 + 데이터 통신(TX/RX)을 케이블 하나로 전부 처리하므로, 별도의
  GND/TX/RX 배선이 필요 없다.

  ★ D3(GPIO0)가 다시 여유 핀이 되어, 비활성화했던 물리 버튼 기능을 복구했다.

  배선: USB-C 케이블 하나로 아두이노 <-> 라즈베리파이 USB 포트 연결. 끝.

  통신 프로토콜 (motion_module.py와 반드시 짝이 맞아야 함):
    파이 -> 아두이노 : "MV,<action>,<speed>\n"
      action: start_patrol / resume_patrol / pause_for_capture /
               stop_patrol(=stop) / forward / backward / turn_left / turn_right /
               heartbeat
    아두이노 -> 파이 : "BAT,<percent>,TEMP,<c>,DIST,<cm>,ZONE,<count>,STATUS,<상태>\n"
      상태: IDLE / ACTIVE / PAUSED / RETURNING / RETURNING_TURN

  ★ 명령 3종의 차이 (매우 중요, 헷갈리기 쉬움):
    - start_patrol      : 완전 새로 시작. zoneCount/턴상태/왕복상태 전부 초기화.
                           (앱에서 순찰을 처음부터 다시 시작할 때, 또는 물리 버튼으로 켤 때)
    - pause_for_capture  : 사진 찍으려고 아주 잠깐 얼려두기. 아무 상태도 건드리지 않음.
                           (Pi가 캡처 직전/직후에만 사용. main_controller.py 전용)
    - stop_patrol / stop : 완전 정지 + 턴상태/마커대기상태 초기화 (왕복상태는 유지).
                           (사람이 진짜로 순찰을 멈추라고 한 경우)

  ★ 구역(zone) 감지 방식 (마커 센서 1개, 두 엣지 모두 사용):
    - 정방향 주행: 진입=HIGH->LOW(zoneCount 증가+2초 정차), 이탈=LOW->HIGH(로그만)
    - 복귀 주행: 로봇이 같은 마커를 반대로 지나가므로 엣지 의미가 뒤바뀐다.
                 진입=LOW->HIGH(zoneCount 감소), 이탈=HIGH->LOW(로그만, 정차 없음)
    - 트랙 형태: 우상단 출발 -> 좌하단 목표지점 도달 -> 180도 회전 -> 좌하단에서
      우상단(출발지)까지 같은 길로 복귀 -> 복귀 완료 시 다시 180도 회전 후 정지.

  ⚠️ 초음파 거리센서(TRIG/ECHO)는 사용 계획이 없어 핀을 버튼/마커 센서로 재배치했다.
  DIST 필드는 프로토콜 호환을 위해 남겨두되 항상 -1.0(미사용) 고정값을 보낸다.
*/

// =========================================================
// ⚙️ 식별 정보 (통신에는 안 쓰이지만 디버깅용으로 유지)
// =========================================================
const char* ROBOT_ID = "R001";
const char* USER_ID = "ddalgi";

// 💡 목표 존(Zone) 마커 개수 - 여기 도달하면 왕복 주행(U턴) 시작
const int TARGET_ZONE = 6;

// =========================================================
// 🔌 하드웨어 핀 매칭 (하드웨어 담당자 실제 빌드 기준)
// =========================================================
const int BUTTON_PIN = 0;          // D3, 버튼 핀 (GND 연결, 내부 풀업 사용) - 복구됨
const int L_RPWM = 5;              // D1
const int L_LPWM = 4;              // D2
const int R_RPWM = 14;             // D5
const int R_LPWM = 12;             // D6
const int R_SENSOR_PIN = 16;       // D0, 우측 라인트레이서 센서
const int L_SENSOR_PIN = 13;       // D7, 좌측 라인트레이서 센서
const int MARKER_SENSOR_PIN = 15;  // D8, 구역(zone) 마커 감지 전용 센서
const int BATTERY_ADC_PIN = A0;

// ★ 온습도 센서용 여분 핀. D0~D3, D5~D8은 전부 사용 중이라 D4(GPIO2)만 비어있다.
// DHT11/DHT22 같은 단일 핀 디지털 센서는 이 자리 하나로 온도+습도 둘 다 읽을 수 있다.
const int DHT_PIN = 2;   // D4

int straightSpeed = 30;
int turnForwardSpeed = 35;
int turnReverseSpeed = 35;
int turnDelay = 60;
int uTurnSpeed = 50;

bool isRunning = false;

// =========================================================
// 📍 구역/마커 + 왕복 주행 상태 변수
// =========================================================
int zoneCount = 0;                    // (구 markerId) 현재 구역 카운트
int lastMarkerState = LOW;

bool isPaused = false;                // 마커 도달 후 2초 정차 중인지
unsigned long pauseStartTime = 0;

bool isReturning = false;             // 왕복 주행 중 복귀 구간인지
int turnState = 0;                    // 0=일반주행, 1=탈출직진, 2=180도 회전
unsigned long turnStateStartTime = 0;

// =========================================================
// 🔘 물리 버튼 (엣지 감지 + 디바운스)
// =========================================================
int lastButtonState = HIGH;
unsigned long lastButtonTime = 0;

// =========================================================
// 🛡️ 안전 타임아웃 - 하트비트 기반
// =========================================================
const unsigned long COMMAND_TIMEOUT_MS = 3000;
unsigned long lastCommandTime = 0;

// ★ pause_for_capture로 얼어있던 시간만큼 마커/턴 타이머를 보정하기 위한 변수
unsigned long captureFreezeStart = 0;

// =========================================================
// 📡 시리얼 명령 파싱 (파이 -> 아두이노)
// =========================================================
String inputBuffer = "";

void checkSerialCommands() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n') {
      processCommand(inputBuffer);
      inputBuffer = "";
    } else if (c != '\r') {
      inputBuffer += c;
    }
  }
}

void resetFullState() {
  zoneCount = 0;
  isPaused = false;
  isReturning = false;
  turnState = 0;
  captureFreezeStart = 0;
}

void processCommand(String line) {
  line.trim();
  if (line.length() == 0) return;

  int firstComma = line.indexOf(',');
  if (firstComma < 0) return;

  String prefix = line.substring(0, firstComma);
  if (prefix != "MV") {
    Serial.println("[CMD 경고] 알 수 없는 프로토콜: " + line);
    return;
  }

  int secondComma = line.indexOf(',', firstComma + 1);
  String action = (secondComma > 0)
      ? line.substring(firstComma + 1, secondComma)
      : line.substring(firstComma + 1);
  int speed = (secondComma > 0) ? line.substring(secondComma + 1).toInt() : straightSpeed;

  lastCommandTime = millis();   // ★ 유효한 MV 명령을 받을 때마다 생존 시각 갱신

  if (action == "heartbeat") {
    return;   // lastCommandTime 갱신 외에 별도 동작 없음

  } else if (action == "start_patrol") {
    isRunning = true;
    resetFullState();
    Serial.println("[CMD] 순찰 시작 (전체 상태 초기화)");

  } else if (action == "resume_patrol") {
    // ★ pause_for_capture로 얼렸던 시간만큼 타이머 보정 후 재개 (상태는 그대로 유지)
    if (captureFreezeStart > 0) {
      unsigned long frozenDuration = millis() - captureFreezeStart;
      pauseStartTime += frozenDuration;
      turnStateStartTime += frozenDuration;
      captureFreezeStart = 0;
    }
    isRunning = true;
    Serial.println("[CMD] 순찰 재개 (상태 유지)");

  } else if (action == "pause_for_capture") {
    // ★ 사진 촬영을 위한 순간 정지. isPaused/isReturning/turnState/zoneCount는
    //   절대 건드리지 않는다 (그대로 얼려두기).
    isRunning = false;
    captureFreezeStart = millis();
    stopMotors();
    Serial.println("[CMD] 캡처를 위해 일시 정지 (상태 보존)");

  } else if (action == "stop_patrol" || action == "stop") {
    isRunning = false;
    isPaused = false;
    turnState = 0;
    captureFreezeStart = 0;
    stopMotors();
    Serial.println("[CMD] 정지 (턴/마커대기 상태 초기화, 왕복상태는 유지)");

  } else if (action == "forward") {
    isRunning = false;
    moveForward(speed);
  } else if (action == "backward") {
    isRunning = false;
    moveBackward(speed);
  } else if (action == "turn_left") {
    isRunning = false;
    turnLeft(speed);
  } else if (action == "turn_right") {
    isRunning = false;
    turnRight(speed);
  } else {
    Serial.println("[CMD 경고] 알 수 없는 action: " + action);
  }
}

// =========================================================
// 🔘 물리 버튼 처리 (엣지 감지 + 50ms 디바운스) - 복구됨
// =========================================================
void checkPhysicalButton() {
  int currentButtonState = digitalRead(BUTTON_PIN);

  if (currentButtonState == LOW && lastButtonState == HIGH &&
      (millis() - lastButtonTime > 50)) {
    isRunning = !isRunning;
    lastCommandTime = millis();   // 물리 조작도 "명령 수신"으로 간주

    if (isRunning) {
      resetFullState();
      Serial.println("🔘 물리 버튼: 순찰 시작 (전체 상태 초기화)");
    } else {
      isPaused = false;
      turnState = 0;
      captureFreezeStart = 0;
      stopMotors();
      Serial.println("🔘 물리 버튼: 정지");
    }
    lastButtonTime = millis();
  }
  lastButtonState = currentButtonState;
}

// =========================================================
// 🚗 초기화
// =========================================================
void setup() {
  Serial.begin(115200);   // ★ 라즈베리파이(USB) 및 motion_module.py의 arduino_baud와 반드시 일치해야 함

  pinMode(L_SENSOR_PIN, INPUT);
  pinMode(R_SENSOR_PIN, INPUT);
  pinMode(MARKER_SENSOR_PIN, INPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);   // 복구됨
  pinMode(R_RPWM, OUTPUT);
  pinMode(R_LPWM, OUTPUT);
  pinMode(L_RPWM, OUTPUT);
  pinMode(L_LPWM, OUTPUT);

  stopMotors();
  lastCommandTime = millis();
  Serial.println("[BOOT] 아두이노 준비 완료 (USB 직결 모드, 왕복주행 지원)");
}

unsigned long lastTelemetryTime = 0;
const unsigned long TELEMETRY_INTERVAL_MS = 2000;

// =========================================================
// 🔁 메인 루프
// =========================================================
void loop() {
  checkSerialCommands();

  // ── 🛡️ 안전장치: 하트비트가 끊기면 자동 정지 + 상태 초기화 ──
  if (millis() - lastCommandTime > COMMAND_TIMEOUT_MS) {
    if (isRunning) {
      Serial.println("[SAFETY] 통신 두절 감지 -> 자동 정지 (상태 초기화)");
    }
    isRunning = false;
    isPaused = false;
    turnState = 0;
    captureFreezeStart = 0;
    stopMotors();
  }

  checkPhysicalButton();

  if (isRunning) {

    // [상태 1] 회전 전 마커 구역 탈출을 위한 0.5초 강제 직진
    if (turnState == 1) {
      analogWrite(R_RPWM, straightSpeed);  digitalWrite(R_LPWM, LOW);
      analogWrite(L_RPWM, straightSpeed);  digitalWrite(L_LPWM, LOW);

      if (millis() - turnStateStartTime >= 500) {
        turnState = 2;
        turnStateStartTime = millis();
        Serial.println("🔄 마커 구역 탈출 완료, 180도 제자리 회전을 시작합니다.");
      }

    // [상태 2] 180도 제자리 시계방향 회전
    } else if (turnState == 2) {
      analogWrite(L_RPWM, uTurnSpeed);
      digitalWrite(L_LPWM, LOW);
      digitalWrite(R_RPWM, LOW);
      analogWrite(R_LPWM, uTurnSpeed);

      int rightValue = digitalRead(R_SENSOR_PIN);
      if ((millis() - turnStateStartTime > 300) && rightValue == HIGH) {
        turnState = 0;

        if (isReturning) {
          isRunning = false;
          isReturning = false;
          Serial.println("🏁 복귀 후 180도 회전 완료! 순찰을 정지합니다.");
        } else {
          isReturning = true;
          Serial.println("▶️ 새로운 라인 진입 확인, 복귀 라인트레이싱을 시작합니다.");
        }
      }

    // [상태 3] 마커 감지 후 2초 정차
    } else if (isPaused) {
      stopMotors();

      if (millis() - pauseStartTime >= 2000) {
        isPaused = false;
        Serial.println("▶️ 2초 대기 완료, 주행을 재개합니다.");

        if (!isReturning && zoneCount == TARGET_ZONE) {
          turnState = 1;
          turnStateStartTime = millis();
          Serial.println("📍 목표 존 도달! 반환점 탈출을 위해 0.5초 직진합니다.");
        }
      }

    // [상태 4] 일반 주행 (라인트레이싱 + 마커 진입/이탈 감지)
    } else if (turnState == 0) {
      int leftValue = digitalRead(L_SENSOR_PIN);
      int rightValue = digitalRead(R_SENSOR_PIN);
      int currentMarkerState = digitalRead(MARKER_SENSOR_PIN);

      // ── 구역 진입/이탈 판정: 정방향과 복귀방향은 엣지가 서로 반대다 ──
      //   정방향: HIGH->LOW = 진입, LOW->HIGH = 이탈
      //   복귀방향: LOW->HIGH = 진입, HIGH->LOW = 이탈
      //   (로봇이 거꾸로 지나가면 같은 마커를 반대 순서로 통과하기 때문)
      bool enteredEdge = !isReturning
          ? (lastMarkerState == HIGH && currentMarkerState == LOW)
          : (lastMarkerState == LOW && currentMarkerState == HIGH);
      bool exitedEdge = !isReturning
          ? (lastMarkerState == LOW && currentMarkerState == HIGH)
          : (lastMarkerState == HIGH && currentMarkerState == LOW);

      if (enteredEdge) {
        if (!isReturning) {
          zoneCount++;
          Serial.print("📍 [정방향] 구역 진입 감지! 현재 zoneCount: ");
          Serial.println(zoneCount);
          isPaused = true;
          pauseStartTime = millis();
          Serial.println("🛑 2초간 정차합니다.");
        } else {
          zoneCount--;
          Serial.print("📍 [복귀주행] 구역 진입(복귀) 감지! 잔여 zoneCount: ");
          Serial.println(zoneCount);
          if (zoneCount <= 0) {
            turnState = 1;
            turnStateStartTime = millis();
            Serial.println("📍 시작 지점 도달! 180도 회전을 위해 0.5초 직진합니다.");
          }
        }

      // ── ★ 구역 이탈 감지: 구역 번호는 안 바뀜, 로그만 ──
      } else if (exitedEdge) {
        Serial.println("🚪 구역 이탈 감지 (zoneCount 변경 없음)");
      }
      lastMarkerState = currentMarkerState;

      // 정차/턴 상태가 아닐 때만 실시간 라인트레이싱 보정
      if (turnState == 0 && !isPaused && isRunning) {
        if (leftValue == LOW && rightValue == HIGH) {           // 우회전
          digitalWrite(R_RPWM, LOW);
          analogWrite(R_LPWM, turnReverseSpeed);
          analogWrite(L_RPWM, turnForwardSpeed);
          digitalWrite(L_LPWM, LOW);
          delay(turnDelay);
        } else if (leftValue == HIGH && rightValue == LOW) {    // 좌회전
          analogWrite(R_RPWM, turnForwardSpeed);
          digitalWrite(R_LPWM, LOW);
          digitalWrite(L_RPWM, LOW);
          analogWrite(L_LPWM, turnReverseSpeed);
          delay(turnDelay);
        } else {                                                 // 직진
          analogWrite(R_RPWM, straightSpeed);  digitalWrite(R_LPWM, LOW);
          analogWrite(L_RPWM, straightSpeed);  digitalWrite(L_LPWM, LOW);
        }
      }
    }
  } else {
    stopMotors();
  }

  // 텔레메트리 주기 전송
  unsigned long now = millis();
  if (now - lastTelemetryTime > TELEMETRY_INTERVAL_MS) {
    lastTelemetryTime = now;
    sendTelemetry();
  }
}

// =========================================================
// 📤 텔레메트리 (배터리/온도/거리/구역/동작상태)
// =========================================================
void sendTelemetry() {
  String opStatus = "IDLE";
  if (isRunning) {
    if (turnState == 2) opStatus = "RETURNING_TURN";
    else if (isPaused) opStatus = "PAUSED";
    else if (isReturning) opStatus = "RETURNING";
    else opStatus = "ACTIVE";
  }

  String line = "BAT," + String(readBatteryPercent(), 1) +
                ",TEMP," + String(readTemperature(), 1) +
                ",DIST," + String(readDistanceCm(), 1) +
                ",ZONE," + String(zoneCount) +
                ",STATUS," + opStatus +
                ",HUM," + String(readHumidity(), 1);

  Serial.println(line);   // USB(하드웨어 시리얼) 하나로 라즈베리파이에게 전송
}

// =========================================================
// 모터 제어 함수
// =========================================================
void moveForward(int speed) {
  digitalWrite(L_RPWM, HIGH); digitalWrite(L_LPWM, LOW);
  digitalWrite(R_RPWM, HIGH); digitalWrite(R_LPWM, LOW);
  analogWrite(L_RPWM, speed); analogWrite(R_RPWM, speed);
}

void moveBackward(int speed) {
  digitalWrite(L_RPWM, LOW); digitalWrite(L_LPWM, HIGH);
  digitalWrite(R_RPWM, LOW); digitalWrite(R_LPWM, HIGH);
  analogWrite(L_RPWM, speed); analogWrite(R_RPWM, speed);
}

void turnLeft(int speed) {
  digitalWrite(L_RPWM, LOW); digitalWrite(L_LPWM, HIGH);
  digitalWrite(R_RPWM, HIGH); digitalWrite(R_LPWM, LOW);
  analogWrite(L_RPWM, speed); analogWrite(R_RPWM, speed);
}

void turnRight(int speed) {
  digitalWrite(L_RPWM, HIGH); digitalWrite(L_LPWM, LOW);
  digitalWrite(R_RPWM, LOW); digitalWrite(R_LPWM, HIGH);
  analogWrite(L_RPWM, speed); analogWrite(R_RPWM, speed);
}

void stopMotors() {
  digitalWrite(L_RPWM, LOW); digitalWrite(L_LPWM, LOW);
  digitalWrite(R_RPWM, LOW); digitalWrite(R_LPWM, LOW);
}

// =========================================================
// 센서 읽기 함수
// =========================================================
float readBatteryPercent() {
  int raw = analogRead(BATTERY_ADC_PIN);
  float voltage = raw * (3.3 / 1023.0) * 3.0;
  float minV = 9.0, maxV = 12.6;
  float percent = (voltage - minV) / (maxV - minV) * 100.0;
  return constrain(percent, 0.0, 100.0);
}

float readTemperature() {
  // ⚠️ 현재는 placeholder(-1.0). 실제 DHT 센서를 D4에 연결하면 아래처럼 바뀐다.
  //
  //   #include <DHT.h>              // 라이브러리 설치: Arduino IDE 라이브러리 매니저에서 "DHT sensor library" 검색
  //   #define DHT_TYPE DHT22        // 실제 모델에 맞게 DHT11 또는 DHT22
  //   DHT dht(DHT_PIN, DHT_TYPE);   // setup()에서 dht.begin(); 한 줄 추가 필요
  //
  //   float readTemperature() {
  //     float t = dht.readTemperature();
  //     return isnan(t) ? -1.0 : t;
  //   }
  return -1.0;
}

float readHumidity() {
  // ⚠️ 현재는 placeholder(-1.0). 실제 DHT 센서 연결 시 위 readTemperature()와
  // 같은 dht 객체로 아래처럼 구현하면 된다.
  //
  //   float readHumidity() {
  //     float h = dht.readHumidity();
  //     return isnan(h) ? -1.0 : h;
  //   }
  return -1.0;
}

float readDistanceCm() {
  return -1.0;  // 초음파 센서 사용 계획 없음 (핀은 버튼/마커 센서로 재배치됨)
}
