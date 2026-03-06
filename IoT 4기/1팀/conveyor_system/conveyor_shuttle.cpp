#include <ESP8266WiFi.h>          // ★ ESP32 → ESP8266
#include <PubSubClient.h>
#include <Servo.h>                // ★ ESP32Servo → Servo

// ================= [핀 정의] =================
#define SERVO_SHUTTLE_PIN D4      // ★ GPIO2 (D4 핀)

// ================= [객체 생성] =================
Servo shuttleServo;
WiFiClient espClient;
PubSubClient client(espClient);

const char* ssid = "team1_Wifi";
const char* password = "12345678";
const char* mqtt_server = "192.168.0.5";

// ★★★ [셔틀 서보 각도] ★★★
const int ANG_SHUTTLE_HOME = 0;
const int ANG_SHUTTLE_PUSH = 120;

unsigned long lastReconnectAttempt = 0;

// ================= [함수 선언] =================
void setup_wifi();
void callback(char* topic, byte* payload, unsigned int length);
boolean reconnect();
void executeShuttleLoad();

void setup() {
    Serial.begin(115200);
    delay(1000);
    
    Serial.println("\n>>> [셔틀 시스템] 초기화 중...");
    Serial.println(">>> 서보 홈 포지션 설정");
    
    shuttleServo.attach(SERVO_SHUTTLE_PIN);
    shuttleServo.write(ANG_SHUTTLE_HOME);
    delay(1000);
    shuttleServo.detach();
    
    setup_wifi();
    client.setServer(mqtt_server, 1883);
    client.setCallback(callback);

    Serial.println(">>> 셔틀 시스템 대기 중");
    Serial.println(">>> MQTT 명령 'SHUTTLE_LOAD' 대기...");
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
    
    delay(10); // CPU 부하 감소
}

// ★★★ [핵심] 셔틀 자동 장전 함수 ★★★
void executeShuttleLoad() {
    Serial.println("\n========================================");
    Serial.println(">>> 셔틀 자동 장전 시작 (5회 반복)");
    Serial.println("========================================");
    
    // ★★★ [1단계] 컨베이어 동시 시작 명령 전송 ★★★
    if (client.connected()) {
        Serial.println(">>> [동시 시작] 컨베이어 명령 전송");
        client.publish("Mobius/Robot_Final/command", "START_CONVEYOR");
        delay(500); // 명령 전송 안정화
    }
    
    // ★★★ [2단계] 셔틀 작업 시작 ★★★
    Serial.println(">>> 셔틀 서보 부착");
    shuttleServo.attach(SERVO_SHUTTLE_PIN);
    shuttleServo.write(ANG_SHUTTLE_HOME);
    delay(1000);
    
    // 5회 왕복
    for (int i = 1; i <= 5; i++) {
        Serial.printf("\n>>> [%d/5] 자석 배출 중...\n", i);
        
        // 밀기
        Serial.printf("   → %d도로 밀기\n", ANG_SHUTTLE_PUSH);
        shuttleServo.write(ANG_SHUTTLE_PUSH);
        delay(1500);
        
        // 복귀
        Serial.printf("   → %d도로 복귀\n", ANG_SHUTTLE_HOME);
        shuttleServo.write(ANG_SHUTTLE_HOME);
        delay(1500);
        
        Serial.printf(">>> [%d/5] 완료\n", i);
    }
    
    // 전원 차단
    delay(200);
    shuttleServo.detach();
    
    Serial.println("\n========================================");
    Serial.println(">>> 셔틀 작업 완료!");
    Serial.println(">>> 컨베이어는 30초 후 자동 정지됨");
    Serial.println("========================================\n");
}

void setup_wifi() {
    delay(10); 
    Serial.print("\n>>> WiFi 연결 시도: ");
    Serial.println(ssid);
    
    WiFi.begin(ssid, password);
    
    int retry = 0;
    while (WiFi.status() != WL_CONNECTED && retry < 20) { 
        delay(500); 
        Serial.print(".");
        retry++; 
    }
    
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\n✅ WiFi 연결 성공");
        Serial.print("IP 주소: ");
        Serial.println(WiFi.localIP());
    } else {
        Serial.println("\n❌ WiFi 연결 실패");
    }
}

void callback(char* topic, byte* payload, unsigned int length) {
    char cmdBuffer[50];
    int cmdLen = (length < 49) ? length : 49;
    memcpy(cmdBuffer, payload, cmdLen);
    cmdBuffer[cmdLen] = '\0';
    String command = String(cmdBuffer);
    
    Serial.printf(">>> [MQTT 수신] Topic: %s | Payload: %s\n", topic, command.c_str());
    
    // ★ 셔틀 로드 명령 처리
    if (command == "SHUTTLE_LOAD") {
        Serial.println(">>> 셔틀 로드 명령 수신!");
        executeShuttleLoad();
    }
}

boolean reconnect() {
    Serial.print(">>> MQTT 연결 시도... ");
    
    if (client.connect("ESP8266_Shuttle")) { // ★ 클라이언트 ID
        Serial.println("성공!");
        
        if (client.subscribe("Mobius/Robot_Final/command")) {
            Serial.println(">>> 토픽 구독 성공: Mobius/Robot_Final/command");
        } else {
            Serial.println("❌ 토픽 구독 실패");
        }
        return true;
    }
    
    Serial.print("실패, rc=");
    Serial.println(client.state());
    return false;
}
