// lib/app_theme.dart
import 'package:flutter/material.dart';

/// [공통 색상 팔레트] 앱 전체에서 사용되는 메인 컬러 정의
/// [에코 오가닉 디자인 포인트] 자연에서 영감을 받은 부드러운 파스텔/어스(Earth) 톤으로 설정
/// 나중에 색상을 바꿀 때는 이 클래스의 색상 코드(0xFF...)만 수정하면 앱 전체에 반영됩니다.
class AppColors {
  static const Color background = Color(0xFFF9F6F0);    // 배경: 부드럽고 따뜻한 오트밀/크림색
  static const Color primary = Color(0xFF7CA982);       // 메인: 편안한 나뭇잎 녹색 (앱바, 주 테마)
  static const Color buttonBg = Color(0xFFE2EBE3);      // 버튼 배경: 아주 옅은 쑥색/민트색
  static const Color buttonText = Color(0xFF3A5A40);    // 버튼 텍스트: 가독성을 위한 짙은 숲속 녹색
  static const Color inputBg = Color(0xFFFFFFFF);       // 입력창 배경: 깨끗한 흰색
  static const Color inputLabel = Color(0xFF8B9D8B);    // 입력창 라벨: 옅은 올리브 회색
  static const Color linkText = Color(0xFFE07A5F);      // 링크 텍스트: 따뜻한 흙빛/테라코타 오렌지 (포인트)
  static const Color alertCardBg = Color(0xFFFDECEF);   // 경고 카드: 연한 꽃분홍

  // 대시보드 및 로봇 제어 패널 색상
  static const Color robotPanelBg = Color(0xFFE9F0EA);  // 제어 패널 배경: 옅은 이끼색
  static const Color sliderThumb = Color(0xFFE07A5F);   // 슬라이더 손잡이: 산딸기 색상 (따뜻한 오렌지)
  static const Color sliderActive = Color(0xFF7CA982);  // 슬라이더 동작 상태: 활기찬 녹색

  // 차트용 테마 색상 (테라코타 오렌지 & 파스텔 블루)
  static const Color chartTemp = Color(0xFFE07A5F);
  static const Color chartHumid = Color(0xFF4A90E2);
}

/// [공통 디자인 테마]
class AppTheme {
  // 입력창 공통 스타일 생성 헬퍼 함수
  static InputDecoration inputDecoration(String labelText, {Widget? suffixIcon}) {
    return InputDecoration(
      labelText: labelText,
      filled: true,
      fillColor: AppColors.inputBg,
      // [에코 오가닉 디자인 포인트] 나뭇잎 모양의 비대칭 모서리 적용
      // BorderRadius.only를 사용하여 왼쪽 위와 오른쪽 아래만 둥글게 깎아 유기적인 형태(조약돌/나뭇잎)를 만듭니다.
      border: const OutlineInputBorder(
        borderRadius: BorderRadius.only(
          topLeft: Radius.circular(20),
          bottomRight: Radius.circular(20),
          topRight: Radius.circular(4),
          bottomLeft: Radius.circular(4),
        ),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(20),
          bottomRight: Radius.circular(20),
          topRight: Radius.circular(4),
          bottomLeft: Radius.circular(4),
        ),
        borderSide: BorderSide(color:AppColors.primary.withValues(alpha:0.5), width: 1.0), // 기본 상태 테두리
      ),
      focusedBorder: const OutlineInputBorder(
        borderRadius: BorderRadius.only(
          topLeft: Radius.circular(20),
          bottomRight: Radius.circular(20),
          topRight: Radius.circular(4),
          bottomLeft: Radius.circular(4),
        ),
        borderSide: BorderSide(color: AppColors.linkText, width: 2.0), // 터치시 테두리: 오렌지색
      ),
      labelStyle: const TextStyle(color: AppColors.inputLabel),
      suffixIcon: suffixIcon,
    );
  }

  // MaterialApp에 일괄 적용할 ThemeData
  static ThemeData get themeData {
    return ThemeData(
      scaffoldBackgroundColor: AppColors.background,
      primaryColor: AppColors.primary,
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        elevation: 0, //상단바이 그림자를 없애 플랫하고 깔끔하게 유지
        centerTitle: false,
      ),
        //버튼의 기본 스타일
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: AppColors.buttonBg,
            foregroundColor: AppColors.buttonText,
            //[디자인 포인트]앱 기본 버튼에도 나뭇잎 형태 적용
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.only(
                topLeft: Radius.circular(24),
                bottomRight: Radius.circular(24),
                topRight: Radius.circular(8),
                bottomLeft: Radius.circular(8),
              ),
            ),
            elevation:0, //인위적인 그림자를 없애 자연그러운 느낌 강조
          ),
        ),
      useMaterial3: true,
    );
  }
}