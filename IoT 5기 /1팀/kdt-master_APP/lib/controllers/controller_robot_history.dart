// lib/controllers/controller_robot_history.dart
import 'package:flutter/material.dart';
import '../core/api_config.dart';
import '../services/service_api.dart';

class RobotHistoryController extends ChangeNotifier {
  List<dynamic> historyLogs = [];
  bool isLoading = false;

  Future<void> fetchHistoryLogs(String userId) async {
    isLoading = true;
    notifyListeners();

    final url = ApiConfig.commandLogsUrl(userId);
    final ApiResult result = await ApiService.get(url);

    // 🌟 안전한 타입 체크 적용
    if (result.success && result.data != null && result.data is Map<String, dynamic>) {
      final Map<String, dynamic> responseData = result.data as Map<String, dynamic>;
      if (responseData['status'] == 'success' && responseData['data'] != null) {
        historyLogs = responseData['data'];
      } else {
        historyLogs = [];
      }
    } else {
      historyLogs = [];
    }

    isLoading = false;
    notifyListeners();
  }
}