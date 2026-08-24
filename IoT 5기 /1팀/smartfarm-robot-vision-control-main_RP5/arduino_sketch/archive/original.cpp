#include <ESP8266WiFi.h>  
#include <PubSubClient.h>

// =========================================================
// ⚙️ [설정] 고유 ID 및 미션 설정 변수
// =========================================================
const char* ROBOT_ID = "R001";
const char* USER_ID = "ddalgi";

// 💡 목표 존(Zone) 마커 개수 설정
const int TARGET_ZONE = 6; 

// 🌐 1. 와이파이 및 서버(MQTT) 설정
const char* WIFI_SSID = "team1_Wifi";       
const char* WIFI_PASS = "12345678";       

const char* MQTT_SERVER = "192.168.0.6";   
const int MQTT_PORT = 1883;

String STATUS_TOPIC;
String COMMAND_TOPIC; 

WiFiClient espClient;
PubSubClient client(espClient);
unsigned long lastMsgTime = 0;
unsigned long lastReconnectAttempt = 0; 

// =========================================================
// 🔌 2. 하드웨어 핀 매칭
// =========================================================
const int BUTTON_PIN = D3;        // 버튼 핀 (GND 연결)
const int L_RPWM = D1;            // 좌측 모터 1
const int L_LPWM = D2;            // 좌측 모터 2
const int R_RPWM = D5;            // 우측 모터 1
const int R_LPWM = D6;            // 우측 모터 2
const int R_SENSOR_PIN = D0;      // 우측 주행 센서
const int L_SENSOR_PIN = D7;      // 좌측 주행 센서
const int MARKER_SENSOR_PIN = D8; // 마커 센서

int straightSpeed = 30;     
int turnForwardSpeed = 35;   
int turnReverseSpeed = 35;   
int turnDelay = 60; 
int uTurnSpeed = 50; 

bool isRunning = false; 

// 버튼 제어 변수
int lastButtonState = HIGH;   
unsigned long lastButtonTime = 0; 

// 마커 인식 및 복귀 주행 제어 변수
int markerId = 0;                 
int lastMarkerState = LOW;        
bool isPaused = false;            
unsigned long pauseStartTime = 0; 

// 왕복 주행 제어 변수
bool isReturning = false;         
int turnState = 0;                // 0: 일반주행, 1: 0.5초 직진 탈출, 2: 180도 회전 중
unsigned long turnStateStartTime = 0; 

// =========================================================
// 📩 3. 서버 명령 수신
// =========================================================
void callback(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  
  if (message.indexOf("start_patrol") >= 0) {
    isRunning = true;
    isPaused = false;
    isReturning = false;
    turnState = 0;
    markerId = 0;
    Serial.println("▶️ 서버 원격 주행(순찰 시작) 명령 확인!");
  } 
  else if (message.indexOf("stop") >= 0) {
    isRunning = false;
    isPaused = false;
    turnState = 0;
    Serial.println("⏸️ 서버 원격 주행(순찰 중지) 명령 확인!");
  }
}

void setup_wifi() {
  delay(10);
  Serial.println("\n[WiFi] 연결 중...");
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n[WiFi] 연결 완료!");
}

boolean reconnect() {
  if (client.connect(ROBOT_ID)) { 
    client.subscribe(COMMAND_TOPIC.c_str());
    return true;
  }
  return false;
}

void setup() {
  Serial.begin(115200);
  
  analogWriteRange(255); 
  
  STATUS_TOPIC = "ddalgi/robot/status/" + String(USER_ID);
  COMMAND_TOPIC = "ddalgi/robot/command/" + String(ROBOT_ID);
  
  pinMode(L_SENSOR_PIN, INPUT);  
  pinMode(R_SENSOR_PIN, INPUT);
  pinMode(MARKER_SENSOR_PIN, INPUT); 

  pinMode(R_RPWM, OUTPUT);       
  pinMode(R_LPWM, OUTPUT);
  pinMode(L_RPWM, OUTPUT);       
  pinMode(L_LPWM, OUTPUT);
  
  pinMode(BUTTON_PIN, INPUT_PULLUP);

  setup_wifi();
  client.setServer(MQTT_SERVER, MQTT_PORT);
  client.setCallback(callback); 
}

void loop() {
  if (!client.connected()) {
    unsigned long now = millis();
    if (now - lastReconnectAttempt > 5000) {
      lastReconnectAttempt = now;
      if (reconnect()) {
        lastReconnectAttempt = 0;
      }
    }
  } else {
    client.loop(); 
  }

  // 물리 버튼 제어
  int currentButtonState = digitalRead(BUTTON_PIN);
  if (currentButtonState == LOW && lastButtonState == HIGH && (millis() - lastButtonTime > 50)) {
    isRunning = !isRunning; 
    if (isRunning) {
      isPaused = false;
      isReturning = false;
      turnState = 0;
      markerId = 0;
      Serial.println("🔘 물리 버튼: 주행 시작");
    } else {
      isPaused = false;
      turnState = 0;
      Serial.println("🔘 물리 버튼: 주행 정지");
    }
    lastButtonTime = millis(); 
  }
  lastButtonState = currentButtonState; 

  // =========================================================
  // 메인 주행 및 상태 머신 로직
  // =========================================================
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
    }
    // [상태 2] 180도 제자리 시계방향 회전
    else if (turnState == 2) {
      analogWrite(L_RPWM, uTurnSpeed);
      digitalWrite(L_LPWM, LOW);
      
      digitalWrite(R_RPWM, LOW);
      analogWrite(R_LPWM, uTurnSpeed);

      int rightValue = digitalRead(R_SENSOR_PIN);
      if ((millis() - turnStateStartTime > 300) && rightValue == HIGH) {
        turnState = 0;
        
        // 복귀 주행 중이었으면 180도 회전을 마친 후 완전히 정지
        if (isReturning) {
          isRunning = false;
          isReturning = false;
          Serial.println("🏁 복귀 후 180도 회전 완료! 시작 정위치를 바라보고 순찰을 정지합니다.");
        } 
        // 정방향 주행 중이었으면 복귀 모드로 전환하여 주행 계속
        else {
          isReturning = true; 
          Serial.println("▶️ 새로운 라인 진입 확인, 복귀 라인트레이싱을 시작합니다.");
        }
      }
    }
    // [상태 3] 정방향 마커 감지 후 2초 정차
    else if (isPaused) {
      digitalWrite(R_RPWM, LOW);  digitalWrite(R_LPWM, LOW);
      digitalWrite(L_RPWM, LOW);  digitalWrite(L_LPWM, LOW);

      if (millis() - pauseStartTime >= 2000) {
        isPaused = false; 
        Serial.println("▶️ 2초 대기 완료, 주행을 재개합니다.");
        
        if (!isReturning && markerId == TARGET_ZONE) {
          turnState = 1; 
          turnStateStartTime = millis();
          Serial.println("📍 목표 존 도달! 반환점 탈출을 위해 0.5초 직진합니다.");
        }
      }
    } 
    // 🚀 [상태 4] 일반 주행 (라인트레이싱 및 마커 감지 동시 수행)
    else if (turnState == 0) {
      int leftValue = digitalRead(L_SENSOR_PIN);
      int rightValue = digitalRead(R_SENSOR_PIN);
      int currentMarkerState = digitalRead(MARKER_SENSOR_PIN);

      // 💡 마커 감지 판단 (HIGH -> LOW Falling Edge)
      if (lastMarkerState == HIGH && currentMarkerState == LOW) {
        if (!isReturning) {
          // 1. 정방향 주행 마커 감지
          markerId++; 
          Serial.print("📍 [정방향] 존 이동 감지! 현재 마커 ID: ");
          Serial.println(markerId);
          
          isPaused = true; 
          pauseStartTime = millis();
          Serial.println("🛑 2초간 정차합니다.");
        } 
        else {
          // 2. 복귀 주행 마커 감지
          markerId--;
          Serial.print("📍 [복귀주행] 마커 통과! 잔여 마커 ID: ");
          Serial.println(markerId);
          
          // 복귀 완료(0번 마커 통과) 시 바로 정지하지 않고 180도 회전 절차 진행
          if (markerId <= 0) {
            turnState = 1; 
            turnStateStartTime = millis();
            Serial.println("📍 시작 지점 도달! 180도 회전을 위해 0.5초 직진합니다.");
          }
        }
      }
      lastMarkerState = currentMarkerState; 

      // 💡 [버그 수정] 정차나 턴 상태가 아닐 때 확실하게 실시간 라인트레이싱 보정 수행
      if (turnState == 0 && !isPaused && isRunning) {
        if (leftValue == LOW && rightValue == HIGH) { // 우회전
          digitalWrite(R_RPWM, LOW);            
          analogWrite(R_LPWM, turnReverseSpeed); 
          analogWrite(L_RPWM, turnForwardSpeed); 
          digitalWrite(L_LPWM, LOW); 
          delay(turnDelay); 
        } 
        else if (leftValue == HIGH && rightValue == LOW) { // 좌회전
          analogWrite(R_RPWM, turnForwardSpeed); 
          digitalWrite(R_LPWM, LOW);             
          digitalWrite(L_RPWM, LOW);             
          analogWrite(L_LPWM, turnReverseSpeed);
          delay(turnDelay); 
        } 
        else { // 직진
          analogWrite(R_RPWM, straightSpeed);  digitalWrite(R_LPWM, LOW);
          analogWrite(L_RPWM, straightSpeed);  digitalWrite(L_LPWM, LOW);
        }
      }
    }
  } 
  else {
    // 완전 정지 상태 
    digitalWrite(R_RPWM, LOW);  digitalWrite(R_LPWM, LOW);
    digitalWrite(L_RPWM, LOW);  digitalWrite(L_LPWM, LOW);
  }

  // 서버 통신 (3초 주기)
  unsigned long now = millis();
  if (client.connected() && (now - lastMsgTime > 3000)) {
    lastMsgTime = now;

    String opStatus = "IDLE";
    if (isRunning) {
      if (turnState == 2) opStatus = "RETURNING_TURN"; 
      else if (isPaused) opStatus = "PAUSED";          
      else if (isReturning) opStatus = "RETURNING";     
      else opStatus = "ACTIVE";                        
    }

    String payload = "{";
    payload += "\"robot_id\":\"" + String(ROBOT_ID) + "\",";
    payload += "\"battery\":" + String(isRunning ? 85 : 95) + ",";
    payload += "\"operating_status\":\"" + opStatus + "\",";
    payload += "\"marker_id\":" + String(markerId < 0 ? 0 : markerId) + ","; 
    payload += "\"lat\":null,";
    payload += "\"lng\":null";
    payload += "}";

    client.publish(STATUS_TOPIC.c_str(), payload.c_str());
  }
}