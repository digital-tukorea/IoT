// lib/core/app_constants.dart

/// 🌟 [전역 상수 관리] 앱 전반에서 반복 사용되는 수치 및 설정값
class AppConstants {
  // 환경 임계값 (알림 기준)
  static const double tempHighLimit = 30.0;
  static const double tempLowLimit = 10.0;
  static const double humidHighLimit = 85.0;
  static const double humidLowLimit = 40.0;

  // 데이터 관리 정책
  static const int maxLogHistory = 100;    // 최대 로그 저장 개수
  static const Duration mqttThrottle = Duration(milliseconds: 500); // UI 갱신 제한 시간

  // 차트 디자인 수치
  static const double chartScrollWidthPerDay = 48.0;
  static const double tempScaleFactor = 2.0; // 온도 시각화 가중치
}
