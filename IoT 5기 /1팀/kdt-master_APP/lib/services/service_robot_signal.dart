// lib/service_robot_signal.dart
import '../core/api_config.dart';
import 'service_api.dart';

class RobotControlService {
  static final RobotControlService _instance = RobotControlService._internal();
  factory RobotControlService() => _instance;
  RobotControlService._internal();

  String _lastSentCommand = 'stop';

  Future<void> sendCommandToRobot({
    required String userId,
    required String robotId,
    required String command,
    String? zoneId,
    required Function(String) onError
  }) async {
      final url = ApiConfig.robotCommandUrl;
      final Map<String, dynamic> requestBody = {
        'user_id': userId,
        'robot_id': robotId,
        'command': command,
      };

      if (zoneId != null && zoneId.isNotEmpty) {
        requestBody['zone_id'] = zoneId;
      }

      final ApiResult result = await ApiService.post(url, requestBody);
      if (!result.success) {
        onError(result.message.isNotEmpty ? result.message : '로봇 명령 전송 실패');
    }
  }

  // [슬라이더 조작 헬퍼 함수]
  void sendSingleCommandForValue({
    required double targetValue,
    required String userId,
    required String robotId,
    String? zoneId,
    required Function(String) onError
  }) {
    String newCommand = (targetValue == 1.0) ? 'start_patrol' : 'stop';

    if (_lastSentCommand != newCommand) {
      _lastSentCommand = newCommand;
      sendCommandToRobot(
          userId: userId,
          robotId: robotId,
          command: newCommand,
          zoneId: zoneId,
          onError: onError
      );
    }
  }
}