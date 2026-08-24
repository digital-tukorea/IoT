/*
  smartfarm_robot.ino

  라즈베리 파이(motion_module.py)와 USB 시리얼로 통신하는 아두이노 스케치.

  프로토콜 (motion_module.py와 반드시 짝이 맞아야 함):
    수신 (파이 -> 아두이노): "MV,<action>,<speed>\n"
        action: forward | backward | turn_left | turn_right | stop
        speed : 0~255
    송신 (아두이노 -> 파이): "BAT,<percent>,TEMP,<c>,DIST,<cm>\n"
        일정 주기(TELEMETRY_INTERVAL_MS)마다 자동 전송

  ⚠️ 아래 모터 제어 부분은 L298N 모터 드라이버 기준 예시입니다.
     실제 사용 중인 드라이버(TB6612FNG, L293D 등)에 맞게 핀 번호와
     제어 방식을 수정하세요.
*/

//#include <Arduino.h>

// ── 핀 설정 (L298N 기준 예시, 실제 배선에 맞게 수정) ──────────
const int MOTOR_L_IN1 = 5;
const int MOTOR_L_IN2 = 6;
const int MOTOR_L_PWM = 9;   // ENA
const int MOTOR_R_IN1 = 7;
const int MOTOR_R_IN2 = 8;
const int MOTOR_R_PWM = 10;  // ENB

const int BATTERY_ADC_PIN = A0;   // 전압 분배 회로를 거쳐 배터리 전압 측정
const int TEMP_SENSOR_PIN = A1;   // 예: TMP36 온도 센서
const int TRIG_PIN = 2;           // 초음파 센서 (예: HC-SR04)
const int ECHO_PIN = 3;

// ── 안전 설정 ──────────────────────────────────────────────
const unsigned long COMMAND_TIMEOUT_MS = 1000;   // 이 시간 동안 명령이 없으면 자동 정지
const unsigned long TELEMETRY_INTERVAL_MS = 2000; // 텔레메트리 전송 주기

unsigned long lastCommandTime = 0;
unsigned long lastTelemetryTime = 0;

void setup() {
  Serial.begin(115200);

  pinMode(MOTOR_L_IN1, OUTPUT);
  pinMode(MOTOR_L_IN2, OUTPUT);
  pinMode(MOTOR_L_PWM, OUTPUT);
  pinMode(MOTOR_R_IN1, OUTPUT);
  pinMode(MOTOR_R_IN2, OUTPUT);
  pinMode(MOTOR_R_PWM, OUTPUT);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  stopMotors();
  lastCommandTime = millis();
}

void loop() {
  // ── 1) 파이로부터 명령 수신 처리 ──
  if (Serial.available() > 0) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() > 0) {
      handleCommand(line);
      lastCommandTime = millis();
    }
  }

  // ── 2) ⭐ 안전장치: 일정 시간 명령이 없으면 자동 정지 ──
  //     파이가 죽거나 USB가 빠져도 로봇이 계속 움직이는 사고를 방지
  if (millis() - lastCommandTime > COMMAND_TIMEOUT_MS) {
    stopMotors();
  }

  // ── 3) 주기적으로 텔레메트리(배터리/온도/거리) 전송 ──
  if (millis() - lastTelemetryTime >= TELEMETRY_INTERVAL_MS) {
    lastTelemetryTime = millis();
    sendTelemetry();
  }
}

// ── 명령 파싱: "MV,forward,60" 형식 ──────────────────────────
void handleCommand(String line) {
  // 형식 검증
  if (!line.startsWith("MV,")) {
    return;
  }

  int firstComma = line.indexOf(',');
  int secondComma = line.indexOf(',', firstComma + 1);
  if (secondComma == -1) {
    return;
  }

  String action = line.substring(firstComma + 1, secondComma);
  int speed = line.substring(secondComma + 1).toInt();
  speed = constrain(speed, 0, 255);

  if (action == "forward") {
    moveForward(speed);
  } else if (action == "backward") {
    moveBackward(speed);
  } else if (action == "turn_left") {
    turnLeft(speed);
  } else if (action == "turn_right") {
    turnRight(speed);
  } else if (action == "stop") {
    stopMotors();
  }
}

// ── 모터 제어 함수 (TODO: 실제 드라이버에 맞게 수정) ──────────
void moveForward(int speed) {
  digitalWrite(MOTOR_L_IN1, HIGH); digitalWrite(MOTOR_L_IN2, LOW);
  digitalWrite(MOTOR_R_IN1, HIGH); digitalWrite(MOTOR_R_IN2, LOW);
  analogWrite(MOTOR_L_PWM, speed);
  analogWrite(MOTOR_R_PWM, speed);
}

void moveBackward(int speed) {
  digitalWrite(MOTOR_L_IN1, LOW); digitalWrite(MOTOR_L_IN2, HIGH);
  digitalWrite(MOTOR_R_IN1, LOW); digitalWrite(MOTOR_R_IN2, HIGH);
  analogWrite(MOTOR_L_PWM, speed);
  analogWrite(MOTOR_R_PWM, speed);
}

void turnLeft(int speed) {
  digitalWrite(MOTOR_L_IN1, LOW); digitalWrite(MOTOR_L_IN2, HIGH);
  digitalWrite(MOTOR_R_IN1, HIGH); digitalWrite(MOTOR_R_IN2, LOW);
  analogWrite(MOTOR_L_PWM, speed);
  analogWrite(MOTOR_R_PWM, speed);
}

void turnRight(int speed) {
  digitalWrite(MOTOR_L_IN1, HIGH); digitalWrite(MOTOR_L_IN2, LOW);
  digitalWrite(MOTOR_R_IN1, LOW); digitalWrite(MOTOR_R_IN2, HIGH);
  analogWrite(MOTOR_L_PWM, speed);
  analogWrite(MOTOR_R_PWM, speed);
}

void stopMotors() {
  digitalWrite(MOTOR_L_IN1, LOW); digitalWrite(MOTOR_L_IN2, LOW);
  digitalWrite(MOTOR_R_IN1, LOW); digitalWrite(MOTOR_R_IN2, LOW);
  analogWrite(MOTOR_L_PWM, 0);
  analogWrite(MOTOR_R_PWM, 0);
}

// ── 텔레메트리 측정 + 전송 ───────────────────────────────────
void sendTelemetry() {
  float batteryPercent = readBatteryPercent();
  float temperatureC = readTemperature();
  float distanceCm = readDistanceCm();

  Serial.print("BAT,");
  Serial.print(batteryPercent, 1);
  Serial.print(",TEMP,");
  Serial.print(temperatureC, 1);
  Serial.print(",DIST,");
  Serial.println(distanceCm, 1);
}

// TODO: 실제 배터리 전압 분배 회로 비율에 맞게 계산식 수정
float readBatteryPercent() {
  int raw = analogRead(BATTERY_ADC_PIN);
  float voltage = raw * (5.0 / 1023.0) * 3.0;  // 예: 1/3 분배 회로 가정
  float minV = 9.0, maxV = 12.6;               // 예: 3셀 리튬 배터리 범위
  float percent = (voltage - minV) / (maxV - minV) * 100.0;
  return constrain(percent, 0.0, 100.0);
}

// TODO: 실제 온도 센서(TMP36 등) 스펙에 맞게 계산식 수정
float readTemperature() {
  int raw = analogRead(TEMP_SENSOR_PIN);
  float voltage = raw * (5.0 / 1023.0);
  return (voltage - 0.5) * 100.0;  // TMP36 기준 공식
}

// 초음파 센서(HC-SR04) 거리 측정
float readDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 30000);  // 30ms 타임아웃
  if (duration == 0) {
    return -1.0;  // 측정 실패
  }
  return duration * 0.034 / 2.0;
}
