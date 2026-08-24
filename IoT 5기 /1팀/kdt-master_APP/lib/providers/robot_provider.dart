import 'package:flutter/material.dart';
import '../services/service_robot_signal.dart';

class RobotProvider extends ChangeNotifier {
  final RobotControlService _robotService = RobotControlService();

  String _currentZone = 'A1';
  double _sliderValue = 0.0;
  bool _isReturningHome = false;

  String get currentZone => _currentZone;
  double get sliderValue => _sliderValue;
  bool get isReturningHome => _isReturningHome;

  void updateZone(String newZone) {
    if (_currentZone != newZone) {
      _currentZone = newZone;
      notifyListeners();
    }
  }

  void updateSliderDragging(double value) {
    _sliderValue = value;
    notifyListeners();
  }

  void updateSliderEnd(double targetValue, String userId, String robotId) {
    _sliderValue = targetValue;
    notifyListeners();

    _robotService.sendSingleCommandForValue(
      targetValue: targetValue,
      userId: userId,
      robotId: robotId,
      zoneId: _currentZone,
      onError: (errorMsg) => debugPrint('로봇제어 에러: $errorMsg'),
    );
  }

  Future<void> sendReturnCommand(String userId, String robotId) async {
    if (_isReturningHome) return;

    _isReturningHome = true;
    notifyListeners();

    await _robotService.sendCommandToRobot(
      userId: userId,
      robotId: robotId,
      command: 'return_home',
      onError: (errorMsg) => debugPrint('귀환 명령 에러: $errorMsg')
    );

    _sliderValue = 0.0;
    _isReturningHome = false;
    notifyListeners();
  }
}