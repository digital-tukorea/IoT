// lib/services/service_auth.dart
import 'package:flutter/foundation.dart';
import '../core/api_config.dart';
import 'service_api.dart';

class AuthService {
  Future<Map<String, dynamic>> login({required String userId, required String password}) async {
    final url = ApiConfig.loginUrl;
    final ApiResult result = await ApiService.post(url, {'user_id': userId, 'password': password});

    // 🌟 강제 형변환(as) 방지 및 안전한 타입 체크 적용
    if (result.success && result.data != null && result.data is Map<String, dynamic>) {
      final Map<String, dynamic> responseData = result.data as Map<String, dynamic>;
      bool isSuccess = responseData['status'] == 'success' || responseData['success'] == true;

      return {
        'success': isSuccess,
        'message': responseData['message'] ?? (isSuccess ? '로그인 성공' : '로그인 실패'),
        'data': responseData['data'] ?? {'user_id': userId, 'name': '사용자'},
      };
    }
    return {'success': false, 'message': result.message.isNotEmpty ? result.message : '서버 통신 실패 또는 응답 오류'};
  }

  Future<Map<String, dynamic>> signup(Map<String, dynamic> requestData) async {
    final url = ApiConfig.signupUrl;
    final ApiResult result = await ApiService.post(url, requestData);

    if (result.success && result.data != null && result.data is Map<String, dynamic>) {
      final Map<String, dynamic> responseData = result.data as Map<String, dynamic>;
      bool isSuccess = responseData['status'] == 'success' || responseData['success'] == true;

      return {
        'success': isSuccess,
        'message': responseData['message'] ?? (isSuccess ? '회원가입 성공' : '회원가입 실패'),
      };
    }
    return {'success': false, 'message': result.message.isNotEmpty ? result.message : '회원가입 요청 실패'};
  }
}
