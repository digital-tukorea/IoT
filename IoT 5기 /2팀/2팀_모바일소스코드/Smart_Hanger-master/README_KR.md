[README_KR.md](https://github.com/user-attachments/files/31362164/README_KR.md)
# 스마트 옷장 관리 서비스 (Smart Closet)

MQTT 통신과 이미지 분석(YOLO) 데이터를 활용하여 효율적으로 옷장을 관리하고, 사용자에게 필요한 알림을 제공하는 안드로이드 애플리케이션입니다.

---

## 🚀 주요 기능

- **의류 데이터 관리**: 옷장에 등록된 의류의 이미지, 설명, YOLO 분석 라벨 등을 확인하고 관리합니다.
- **스마트 알림 시스템**: 일주일 이상 입지 않은 옷이 있을 경우 사용자에게 빨래를 권장하는 푸시 알림을 발송합니다.
- **MQTT 통신 연동**: 실시간으로 옷장 상태나 데이터를 주고받을 수 있는 MQTT 프로토콜이 구현되어 있습니다.

---

## 📁 프로젝트 구조 (Android)

프로젝트의 주요 패키지 및 구성 요소는 다음과 같습니다.

| 패키지 경로 | 역할 및 설명 |
| :--- | :--- |
| `activity` | 애플리케이션의 주요 화면(UI)을 담당하는 액티비티 모음 (`MainActivity` 등) |
| `fragment` | 화면의 부분 UI를 구성하는 프래그먼트 (`HomeFragment` 등) |
| `model` | 의류(`Clothing`) 등 앱에서 사용하는 데이터 객체 정의 |
| `receiver` | 시스템 이벤트나 예약된 알람을 수신하는 브로드캐스트 리시버 (`LaundryAlarmReceiver`) |
| `repository` | Firebase나 API 서버 등 데이터 소스로부터 정보를 가져오는 로직 (`ClothingRepository`) |
| `mqtt` | MQTT 통신 연결 및 메시지 송수신을 위한 헬퍼 클래스 |
| `util` / `helper` | 날짜 형식 변환, 이미지 처리 등 공통 유틸리티 함수 |

---

## 🧺 빨래 알림 로직 (`LaundryAlarmReceiver`)

이 앱은 사용자가 옷을 청결하게 관리할 수 있도록 돕는 알림 기능을 포함하고 있습니다.

- **알림 조건**:
    - `Clothing` 모델의 `createdAt` 데이터를 기준으로 현재 시간과 **7일(일주일)** 이상 차이가 날 경우.
    - (시연용) 특정 ID(예: ID #1)를 가진 의류는 즉시 빨래 대상에 포함.
- **스케줄링**:
    - `AlarmManager`를 사용하여 매일 지정된 시간(예: 오전 00:49)에 알림 여부를 체크합니다.
    - 알림이 발생하면 `NotificationChannel`을 통해 푸시 메시지를 사용자 기기로 전송합니다.

---

## 🛠 기술 스택

- **Language**: Java / Kotlin
- **Networking**: MQTT, Retrofit/OkHttp (추정)
- **Image Analysis**: YOLO (Object Detection Labels)
- **UI Framework**: Android XML / Jetpack (Partial)
