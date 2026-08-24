// lib/api_config.dart

class ApiConfig {
  // 1. 서버 IP 및 포트 설정 (이곳만 변경하면 전체 앱에 적용됨)
  static const String serverIp = '15.134.203.220'; // 백엔드 서버 IP
  static const int restPort = 12345;              // HTTP REST API 포트
  static const int mqttPort = 1883;               // MQTT 포트

  // 2. Base URL 정의
  static const String baseUrl = 'http://$serverIp:$restPort';

  // 3. API 엔드포인트 URL 모음
  // 1-1. 회원가입 API
  static const String signupUrl = '$baseUrl/api/auth/signup';
  // 1-2. 로그인 API
  static const String loginUrl = '$baseUrl/api/auth/login';
  // 1-3. 신규 로봇 등록 API (필요 시 사용)
  static const String robotRegisterUrl = '$baseUrl/api/robot/register';
  // 1-4. 구역 설정 API (필요 시 사용)
  static const String zoneSetupUrl = '$baseUrl/api/zone/setup';
  // 1-5. 데이터 완전 삭제
  static const String dataResetUrl = '$baseUrl/api/zones/batch/manage';


  // 3-4. 로봇 제어 명령 전송 API (POST /api/robot/command)
  static const String robotCommandUrl = '$baseUrl/api/robot/command';

  // 2-1. 특정 로봇 실시간 상태 조회 API (GET /api/robot/status/{robot_id})
  static String robotStatusUrl(String robotId, String userId) => '$baseUrl/api/robot/status/$robotId?user_id=$userId';
  // 2-2. 유저 전체 구역 및 재배 이력 조회 API (GET /api/user/zones)
  static String userZonesUrl(String userId) => '$baseUrl/api/user/zones?user_id=$userId';
  // 2-3. 작물 상태 그룹 자동 집계 API (GET /api/user/crop/summary)
  static String cropSummaryUrl(String userId, String cropId) => '$baseUrl/api/user/crop/summary?user_id=$userId&crop_id=$cropId';
  // 2-4. 최근 환경 로그 조회 API (GET /api/logs/env)
  static String envLogsUrl(String userId) => '$baseUrl/api/logs/env?user_id=$userId';
  // 2-4. 최근 작물 이상/촬영 로그 조회 API (GET /api/logs/crop)
  static String cropLogsUrl(String userId) => '$baseUrl/api/logs/crop?user_id=$userId';
  // 2-5. 로봇 제어 명령 이력 조회 API (GET /api/logs/command)
  static String commandLogsUrl(String userId) => '$baseUrl/api/logs/command?user_id=$userId';

  // 4. MQTT 토픽 수신 규격 정의
  //  질병 경고 수신 토픽 (서버 -> 앱)
  static String diseaseAlertTopic(String userId) => 'ddalgi/alert/disease/$userId';
}