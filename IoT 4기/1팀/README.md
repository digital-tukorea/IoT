🏭 AIoT 기반 자율 순찰 및 스마트 자원 순환 시스템

#1. 📖 프로젝트 개요
본 프로젝트는 제조 및 건설 현장의 자원 수거/분류 과정에서 발생하는 인력 의존성과 안전 사고 문제를 해결하기 위해 개발되었습니다.
단순한 하드웨어 자동화를 넘어 국제 표준 IoT 플랫폼(Mobius 4.0)을 활용한 중앙에서 뻗어나가는 아키텍처를 구축하여 이기종 기기 간의 M2M 연동과 실시간 관제(Digital Twin)를 구현했습니다.

팀원: 최승범(조장), 권재훈, 박건무, 배민성, 방우혁

주요 성과: 모터 제어 및 전력 안정화, PostgreSQL 기반 대용량 데이터 파이프라인 구축


#2. 🏗️ 개발 및 실행 환경 (Tech Stack)
💻 Hardware
- Edge / Controller: Raspberry Pi 5, Arduino Mega, ESP32

- Sensors & Actuators: LiDAR, RFID Reader, High-Torque Servo Motors, Step Motors

- Power Management: LM2596 DC-DC Buck Converter (전압 강하 방지용)

⚙️ Software & AI
- Server & DB: Node.js (Mobius 4.0), PostgreSQL 17

- AI & Vision: YOLOv8, OpenCV, Python

- Frontend / Mobile: React, HTML5/CSS/JS, Android (Java)

📡 Network & Protocols
- Wireless: WiFi, MQTT (초저지연 제어), HTTP/REST API (데이터 로깅)

- Wired: UART/Serial (내부 MCU 간 통신)

#3. 🌐 시스템 아키텍처 (System Architecture)
<img width="1024" height="565" alt="image" src="https://github.com/user-attachments/assets/da1c38e5-6ea7-4e67-ae02-1dc643ed953e" />
- Core Server (Hub): 중앙의 Mobius 4.0 서버가 모든 데이터를 통합 관리하며 oneM2M 표준 리소스 트리(AE, CNT, CIN)를 적용하여 확장성 확보.

- M2M 연동: AGV 로봇(하역 완료) ➡️ Mobius 서버(트리거 발행) ➡️ Smart Sorter(분류 셔틀 작동)로 이어지는 유기적인 프로세스 구축.

#4. 서버 구축
##PostgreSQL
<img width="2268" height="496" alt="PostgreSQL" src="https://github.com/user-attachments/assets/e8ea55d5-41d6-479d-8925-1d54a0510e11" />

##AE_CNT
<img width="864" height="1475" alt="AE_CNT" src="https://github.com/user-attachments/assets/1cea7c94-40bd-4507-9767-7d470b58e6f1" />

##Terminal
<img width="1179" height="1530" alt="모비우스4버전_터미널" src="https://github.com/user-attachments/assets/e61b8c85-9f3f-4d94-985f-6b72ede70b93" />


#5. 프로젝트 하드웨어 및 시스템 시각 자료.
##하드웨어
###Robot1
![로봇4](https://github.com/user-attachments/assets/8e2717c4-6353-4ca2-8b37-758b59662edc)

###Robot2
![로봇3](https://github.com/user-attachments/assets/b7993fbd-5113-483b-a83c-6074bd3a6d58)


###Convetor1
![컨베이어2](https://github.com/user-attachments/assets/4b418226-6bc9-4d67-9087-744e003f60a7)

###Convetor2
![컨베이어3](https://github.com/user-attachments/assets/f5160a9b-127c-41c1-9c8b-7bf9fa1e266d)


## 대시보드
###dash1
<img width="2879" height="1673" alt="대시보드1" src="https://github.com/user-attachments/assets/09d51fbe-a897-4ae2-b727-0856de8d3c2d" />

###dash2
<img width="2879" height="1611" alt="KDT_SEF_Dashboard1" src="https://github.com/user-attachments/assets/e9ec8547-0aec-4a36-92ab-fb83b003af99" />

###dash3
<img width="2879" height="1634" alt="KDT_SEF_Dashboard3" src="https://github.com/user-attachments/assets/db45d375-c366-45e0-8ec2-4bada1449682" />

