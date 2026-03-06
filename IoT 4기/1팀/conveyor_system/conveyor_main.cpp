#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ESP32Servo.h>
#include <AccelStepper.h>
#include <vector>

#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"

// ================= [핀 정의] =================
#define IN1 17
#define IN2 5
#define IN3 18
#define IN4 19
#define SERVO_SORT_A_PIN 33
#define SERVO_SORT_B_PIN 25
#define IR_ENTRY_PIN 26

// ================= [객체 생성] =================
AccelStepper conveyor(AccelStepper::FULL4WIRE, IN1, IN2, IN3, IN4);
Servo sortAServo;
Servo sortBServo;
WiFiClient espClient;
PubSubClient client(espClient);

const char* ssid = "team1_Wifi";
const char* password = "12345678";
const char* mqtt_server = "192.168.0.5";

const int SPEED_VAL = -80;

// ★★★ [타이밍 확정] ★★★
const unsigned long TIME_DETECT_WINDOW = 3000; 
const unsigned long TIME_TO_A = 3900;
const unsigned long TIME_TO_B = 9500;
const unsigned long TIME_EXIT = 15000;

// ★★★ [서보 각도 확정] ★★★
const int ANG_A_HOME = 0;    
const int ANG_A_ACTION = 100; 
const int ANG_B_HOME = 0;  
const int ANG_B_ACTION = 100;

const int SORT_CYCLE_TIME = 1500; 

// ★★★ [자동 정지 타이머] ★★★
const unsigned long AUTO_STOP_TIME_MS = 60000; // 50초
unsigned long conveyorStartTime = 0;
bool autoStopEnabled = false;

// ================= [구조체] =================
enum ItemState { DETECTING, MOVING_TO_A, MOVING_TO_B, MOVING_TO_EXIT, PROCESSED };

struct Item {
    unsigned long entryTime;
    int type;      
    ItemState state;
    bool actionDone;
};

std::vector<Item> beltQueue;

enum SystemState { IDLE, RUNNING, SORTING };
SystemState sysState = IDLE;

unsigned long lastReconnectAttempt = 0;

// ================= [함수 선언] =================
void setup_wifi();
void callback(char* topic, byte* payload, unsigned int length);
boolean reconnect();
void handleSensors();
void updateItems();
void executeSort(char target, int pin, int angleHome, int angleAction);
void releaseMotor();
void send_sort_result(String type);
void checkAutoStop();

void setup() {
    WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0); 
    Serial.begin(115200);
    pinMode(IR_ENTRY_PIN, INPUT);
    
    pinMode(IN1, OUTPUT); pinMode(IN2, OUTPUT); 
    pinMode(IN3, OUTPUT); pinMode(IN4, OUTPUT);

    conveyor.setMaxSpeed(2000);
    conveyor.setSpeed(SPEED_VAL);
    
    Serial.println(">>> 서보 초기화: 0도 정렬");
    
    sortAServo.attach(SERVO_SORT_A_PIN); 
    sortAServo.write(ANG_A_HOME);
    
    sortBServo.attach(SERVO_SORT_B_PIN); 
    sortBServo.write(ANG_B_HOME);
    
    delay(1500); 
    
    sortAServo.detach(); 
    sortBServo.detach();
    
    setup_wifi();
    client.setServer(mqtt_server, 1883);
    client.setCallback(callback);

    Serial.println(">>> [컨베이어 시스템] 대기 중 (IDLE 모드)");
    Serial.println(">>> MQTT 명령 'START_CONVEYOR' 대기...");
}

void loop() {
    if (!client.connected()) {
        unsigned long now = millis();
        if (now - lastReconnectAttempt > 5000) {
            lastReconnectAttempt = now;
            if (reconnect()) lastReconnectAttempt = 0;
        }
    } else {
        client.loop();
    }

    if (sysState == RUNNING) {
        conveyor.runSpeed(); 
        handleSensors();     
        updateItems();
        
        if (autoStopEnabled) {
            checkAutoStop();
        }
    } 
}

// ★★★ [자동 정지 체크] ★★★
void checkAutoStop() {
    unsigned long elapsed = millis() - conveyorStartTime;
    
    if (elapsed >= AUTO_STOP_TIME_MS) {
        Serial.println("\n========================================");
        Serial.printf(">>> [자동 정지] %d초 경과\n", AUTO_STOP_TIME_MS / 1000);
        Serial.println("========================================\n");
        
        sysState = IDLE;
        conveyor.stop();
        releaseMotor();
        autoStopEnabled = false;
        beltQueue.clear();
    } else {
        static unsigned long lastLog = 0;
        if (elapsed - lastLog >= 10000) {
            int remaining = (AUTO_STOP_TIME_MS - elapsed) / 1000;
            Serial.printf(">>> 자동 정지까지 %d초 남음\n", remaining);
            lastLog = elapsed;
        }
    }
}

void handleSensors() {
    static bool lastState = HIGH;
    bool currentState = digitalRead(IR_ENTRY_PIN);

    if (lastState == HIGH && currentState == LOW) {
        Serial.println(">>> [신규] 물체 진입!");
        Item newItem = { millis(), 0, DETECTING, false };
        beltQueue.push_back(newItem);
    }
    lastState = currentState;
}

void updateItems() {
    unsigned long now = millis();

    for (auto &it : beltQueue) {
        if (it.state == PROCESSED) continue;

        unsigned long elapsed = now - it.entryTime;

        if (it.state == DETECTING) {
             if (elapsed >= TIME_DETECT_WINDOW) {
                 if (it.type == 0) it.type = 3; 
                 it.state = MOVING_TO_A; 
             }
        }
        
        if (!it.actionDone && elapsed >= TIME_TO_A) {
            if (it.type == 2) { 
                Serial.println(">>> [A 도착] 정지 및 분류 시작");
                sysState = SORTING; 
                
                executeSort('A', SERVO_SORT_A_PIN, ANG_A_HOME, ANG_A_ACTION);
                send_sort_result("SORT_CAN");
                
                for (auto &q : beltQueue) q.entryTime += SORT_CYCLE_TIME;
                
                it.actionDone = true;
                sysState = RUNNING;
                return;
            }
        }

        if (!it.actionDone && elapsed >= TIME_TO_B) {
            if (it.type == 1) { 
                Serial.println(">>> [B 도착] 정지 및 분류 시작");
                sysState = SORTING;
                
                executeSort('B', SERVO_SORT_B_PIN, ANG_B_HOME, ANG_B_ACTION);
                send_sort_result("SORT_BAT");
                
                for (auto &q : beltQueue) q.entryTime += SORT_CYCLE_TIME;
                
                it.actionDone = true;
                sysState = RUNNING;
                return;
            }
        }

        if (elapsed >= TIME_EXIT) {
            if (!it.actionDone) send_sort_result("SORT_ETC");
            it.state = PROCESSED;
        }
    }
    
    for (auto it = beltQueue.begin(); it != beltQueue.end(); ) {
        if (it->state == PROCESSED) it = beltQueue.erase(it);
        else ++it;
    }
}

void executeSort(char target, int pin, int angleHome, int angleAction) {
    conveyor.stop();
    releaseMotor(); 
    delay(100); 

    Servo* s = (target == 'A') ? &sortAServo : &sortBServo;
    if (!s->attached()) s->attach(pin);
    
    s->write(angleAction);
    delay(800); 

    s->write(angleHome);
    delay(500); 

    s->detach();
    delay(100);

    Serial.println(">>> 컨베이어 재가동");
    conveyor.setSpeed(SPEED_VAL); 
}

void releaseMotor() {
    digitalWrite(IN1, LOW);
    digitalWrite(IN2, LOW);
    digitalWrite(IN3, LOW);
    digitalWrite(IN4, LOW);
}

void send_sort_result(String type) {
    if (client.connected()) {
        client.publish("factory/conveyor/log", type.c_str());
    }
}

void setup_wifi() {
    delay(10); 
    WiFi.begin(ssid, password);
    int retry = 0;
    while (WiFi.status() != WL_CONNECTED && retry < 10) { 
        delay(500); 
        Serial.print(".");
        retry++; 
    }
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\n>>> WiFi 연결 성공");
    }
}

void callback(char* topic, byte* payload, unsigned int length) {
    char cmdBuffer[50];
    int cmdLen = (length < 49) ? length : 49;
    memcpy(cmdBuffer, payload, cmdLen);
    cmdBuffer[cmdLen] = '\0';
    String command = String(cmdBuffer);
    
    Serial.printf(">>> [MQTT 수신] Topic: %s | Payload: %s\n", topic, command.c_str());
    
    // ★★★ [컨베이어 시작 명령 - 30초 타이머 시작] ★★★
    if (command == "START_CONVEYOR") {
        if (sysState == IDLE) {
            Serial.println("\n========================================");
            Serial.println(">>> 컨베이어 가동 시작!");
            Serial.printf(">>> %d초 후 자동 정지 예정\n", AUTO_STOP_TIME_MS / 1000);
            Serial.println("========================================\n");
            
            sysState = RUNNING;
            conveyor.setSpeed(SPEED_VAL);
            
            conveyorStartTime = millis();
            autoStopEnabled = true;
        } else {
            Serial.println(">>> 이미 가동 중입니다.");
        }
        return;
    }
    
    // ★★★ [컨베이어 수동 정지] ★★★
    if (command == "STOP_CONVEYOR") {
        Serial.println(">>> 컨베이어 수동 정지!");
        sysState = IDLE;
        conveyor.stop();
        releaseMotor();
        autoStopEnabled = false;
        beltQueue.clear();
        return;
    }
    
    // 기존 분류 명령 처리 (1=배터리, 2=캔, 3=기타)
    int cmd = command.toInt();
    if (cmd >= 1 && cmd <= 3) {
        for (auto &it : beltQueue) {
            if (it.type == 0) {
                it.type = cmd;
                Serial.printf(">>> [매핑] Type %d 할당\n", cmd);
                break;
            }
        }
    }
}

boolean reconnect() {
    if (client.connect("ESP32_Conveyor")) {
        client.subscribe("Mobius/Robot_Final/command");
        Serial.println(">>> MQTT 재연결 성공");
        return true;
    }
    return false;
}
