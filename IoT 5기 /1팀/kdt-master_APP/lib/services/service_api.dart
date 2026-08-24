// lib/services/service_api.dart
import 'dart:async'; // 🌟 TimeoutException 처리를 위해 추가
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

class ApiResult {
  final bool success;
  final dynamic data;
  final String message;

  ApiResult({required this.success, this.data, this.message = ''});
}

class ApiService {
  static Future<ApiResult> get(String url) async {
    try {
      final uri = Uri.parse(url);
      final response = await http.get(uri).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        return ApiResult(success: true, data: jsonDecode(utf8.decode(response.bodyBytes)));
      } else {
        debugPrint('❌ API 에러 (상태 코드: ${response.statusCode})');
        return ApiResult(success: false, message: '서버 오류 (${response.statusCode})');
      }
    } on TimeoutException catch (_) {
      // 🌟 타임아웃 예외 별도 처리
      return ApiResult(success: false, message: '서버 요청 시간이 초과되었습니다.');
    } catch (e) {
      debugPrint('❌ 네트워크 예외 발생: $e');
      return ApiResult(success: false, message: '네트워크 연결이 원활하지 않습니다.');
    }
  }

  static Future<ApiResult> post(String url, Map<String, dynamic> body) async {
    try {
      final uri = Uri.parse(url);
      final response = await http.post(
        uri,
        headers: {'Content-Type': 'application/json'}, // 향후 토큰 확장 가능 지점
        body: jsonEncode(body),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200 || response.statusCode == 201) {
        return ApiResult(success: true, data: jsonDecode(utf8.decode(response.bodyBytes)));
      } else {
        debugPrint('❌ API 에러 (상태 코드: ${response.statusCode})');
        return ApiResult(success: false, message: '서버 오류 (${response.statusCode})');
      }
    } on TimeoutException catch (_) {
      return ApiResult(success: false, message: '서버 요청 시간이 초과되었습니다.');
    } catch (e) {
      debugPrint('❌ 네트워크 예외 발생: $e');
      return ApiResult(success: false, message: '네트워크 연결이 원활하지 않습니다.');
    }
  }
}
