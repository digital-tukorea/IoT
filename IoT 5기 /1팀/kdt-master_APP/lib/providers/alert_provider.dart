// lib/providers/alert_provider.dart
import 'dart:async';
import 'package:flutter/material.dart';
import '../core/api_config.dart';
import '../services/service_api.dart';
import '../services/service_mqtt.dart';

class AlertProvider extends ChangeNotifier {
  List<Map<String, dynamic>> alertLogs = [];
  List<Map<String, dynamic>> inspectionLogs = [];
  bool isLoading = false;

  bool get isConnected => MqttService().isConnected;

  // 🌟 읽지 않은 알림 개수 계산 Getter 추가
  int get unreadAlertCount => alertLogs.where((log) => log['isRead'] != true).length;

  static const int _maxLogCount = 100;
  bool _isDisposed = false;
  StreamSubscription? _mqttSubscription;
  Timer? _throttleTimer;

  @override
  void dispose() {
    _isDisposed = true;
    _mqttSubscription?.cancel();
    _throttleTimer?.cancel();
    super.dispose();
  }

  void _throttledNotify() {
    if (_throttleTimer?.isActive ?? false) return;
    _throttleTimer = Timer(const Duration(milliseconds: 500), () {
      if (!_isDisposed) notifyListeners();
    });
  }

  // 🌟 항목을 읽음 처리하는 메서드 추가
  void markAlertAsRead(Map<String, dynamic> log) {
    if (log['isRead'] != true) {
      log['isRead'] = true;
      notifyListeners();
    }
  }

  void init(String userId) {
    MqttService().connect(userId);
    _fetchHistoryLogs(userId);

    _mqttSubscription?.cancel();
    _mqttSubscription = MqttService().messageStream.listen((data) {
      final topic = data['topic']?.toString() ?? '';
      bool changed = false;

      if (topic == ApiConfig.diseaseAlertTopic(userId)) {
        _addLogToList(alertLogs, data);
        _addLogToList(inspectionLogs, data);
        changed = true;
      } else if (topic == 'ddalgi/robot/status' && data.containsKey('health_status')) {
        _addLogToList(inspectionLogs, data);
        changed = true;
      }

      if (changed) _throttledNotify();
    });
  }

  void _addLogToList(List<Map<String, dynamic>> list, Map<String, dynamic> data) {
    // 🌟 새로 추가되는 데이터는 기본적으로 '읽지 않음(false)' 처리
    if (!data.containsKey('isRead')) {
      data['isRead'] = false;
    }
    list.insert(0, data);
    if (list.length > _maxLogCount) list.removeLast();
  }

  Future<void> _fetchHistoryLogs(String userId) async {
    isLoading = true;
    notifyListeners();

    final result = await ApiService.get(ApiConfig.cropLogsUrl(userId));
    if (result.success && result.data != null) {
      final List<dynamic> logs = result.data['data'] ?? [];
      alertLogs.clear();
      inspectionLogs.clear();
      for (var log in logs) {
        final logMap = Map<String, dynamic>.from(log);
        logMap['isRead'] = false; // 🌟 API로 불러온 과거 데이터도 기본 안읽음 처리
        _addLogToList(inspectionLogs, logMap);
        if (['경고', '위험'].contains(logMap['health_status'])) {
          _addLogToList(alertLogs, logMap);
        }
      }
    }
    isLoading = false;
    notifyListeners();
  }
}
