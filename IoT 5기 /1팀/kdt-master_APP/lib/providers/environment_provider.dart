import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../services/service_mqtt.dart';
import '../core/app_constants.dart';
import 'dart:async';

class EnvDailyData {
  final String date;
  double maxTemp, minTemp, maxHumid, minHumid;
  EnvDailyData({required this.date, required this.maxTemp, required this.minTemp, required this.maxHumid, required this.minHumid});
}

class EnvironmentProvider extends ChangeNotifier {
  final Map<String, EnvDailyData> _dailyMap = {};
  final Map<String, String> _dateNotes = {}; 
  List<EnvDailyData> _dailyLogs = [];
  int _selectedRange = 7;
  bool _isLoading = false; // 🌟 추가
  bool _isDisposed = false;
  StreamSubscription? _mqttSubscription;
  Timer? _throttleTimer;

  List<EnvDailyData> get dailyLogs => _dailyLogs;
  Map<String, EnvDailyData> get dailyMap => _dailyMap;
  int get selectedRange => _selectedRange;
  bool get isLoading => _isLoading; // 🌟 추가

  EnvironmentProvider() { _generateDummyEnvironmentLogs(_selectedRange); }

  @override
  void dispose() {
    _isDisposed = true;
    _mqttSubscription?.cancel();
    _throttleTimer?.cancel();
    super.dispose();
  }

  void _throttledNotify() {
    if (_throttleTimer?.isActive ?? false) return;
    _throttleTimer = Timer(AppConstants.mqttThrottle, () {
      if (!_isDisposed) notifyListeners();
    });
  }

  void initMqtt(String userId) {
    if (_dailyLogs.isEmpty) _generateDummyEnvironmentLogs(_selectedRange);
    _mqttSubscription?.cancel();
    _mqttSubscription = MqttService().messageStream.listen((data) {
      if (data['topic']?.toString().contains('env/log') ?? false) _updateWithRealtimeData(data);
    });
  }

  void _updateWithRealtimeData(Map<String, dynamic> data) {
    if (_dailyLogs.isEmpty) return;
    final double t = (data['temperature'] ?? 0.0).toDouble();
    final double h = (data['humidity'] ?? 0.0).toDouble();
    var today = _dailyLogs.last;
    bool changed = false;
    if (t > today.maxTemp) { today.maxTemp = t; changed = true; }
    if (t < today.minTemp) { today.minTemp = t; changed = true; }
    if (h > today.maxHumid) { today.maxHumid = h; changed = true; }
    if (h < today.minHumid) { today.minHumid = h; changed = true; }
    if (changed) { _dailyMap[today.date] = today; _throttledNotify(); }
  }

  void _generateDummyEnvironmentLogs(int count) {
    final random = math.Random();
    final now = DateTime.now();
    _dailyLogs.clear(); _dailyMap.clear();
    for (int i = 0; i < count; i++) {
      final dateStr = '${now.subtract(Duration(days: (count - 1) - i)).month.toString().padLeft(2,'0')}/${now.subtract(Duration(days: (count - 1) - i)).day.toString().padLeft(2,'0')}';
      double minT = 10.0 + random.nextDouble() * 10;
      double maxT = minT + 10.0 + random.nextDouble() * 5;
      final newData = EnvDailyData(date: dateStr, maxTemp: _fix(maxT), minTemp: _fix(minT), maxHumid: _fix(50.0+random.nextDouble()*20), minHumid: _fix(20.0+random.nextDouble()*15));
      _dailyLogs.add(newData); _dailyMap[dateStr] = newData;
    }
  }

  double _fix(double v) => double.parse(v.toStringAsFixed(1));
  String getNoteForDate(String ymd) => _dateNotes[ymd] ?? '';
  void saveNoteForDate(String ymd, String note) { _dateNotes[ymd] = note; notifyListeners(); }
  void setRange(int r) { _selectedRange = r; _generateDummyEnvironmentLogs(r); notifyListeners(); }

  // 🌟 외부 화면에서 호출하는 공통 메서드
  Future<void> fetchEnvironmentLogs(String userId) async {
    initMqtt(userId);
  }

  // 전역 상수를 사용한 차트 데이터 변환
  List<FlSpot> get maxTempSpots => _dailyLogs.asMap().entries.map((e) => FlSpot(e.key.toDouble(), e.value.maxTemp * AppConstants.tempScaleFactor)).toList();
  List<FlSpot> get minTempSpots => _dailyLogs.asMap().entries.map((e) => FlSpot(e.key.toDouble(), e.value.minTemp * AppConstants.tempScaleFactor)).toList();
  List<FlSpot> get maxHumidSpots => _dailyLogs.asMap().entries.map((e) => FlSpot(e.key.toDouble(), e.value.maxHumid)).toList();
  List<FlSpot> get minHumidSpots => _dailyLogs.asMap().entries.map((e) => FlSpot(e.key.toDouble(), e.value.minHumid)).toList();
  List<String> get dates => _dailyLogs.map((e) => e.date).toList();
}
