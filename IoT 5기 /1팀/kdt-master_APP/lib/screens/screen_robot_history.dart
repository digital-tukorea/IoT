// lib/screens/screen_robot_history.dart
import 'package:flutter/material.dart';
import '../core/app_theme.dart';
import '../widgets/app_widgets.dart';
import '../controllers/controller_robot_history.dart';

class RobotHistoryScreen extends StatefulWidget {
  final String currentUserId;
  const RobotHistoryScreen({super.key, required this.currentUserId});

  @override
  State<RobotHistoryScreen> createState() => _RobotHistoryScreenState();
}

class _RobotHistoryScreenState extends State<RobotHistoryScreen> {
  final RobotHistoryController _controller = RobotHistoryController();

  @override
  void initState() {
    super.initState();
    _controller.fetchHistoryLogs(widget.currentUserId);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            padding: const EdgeInsets.all(32),
            decoration: BoxDecoration(color: AppColors.primary.withValues(alpha: 0.1), shape: BoxShape.circle),
            child: Icon(Icons.history_rounded, size: 72, color: AppColors.primary.withValues(alpha: 0.5)),
          ),
          const SizedBox(height: 16),
          const Text('최근 로봇 제어 기록이 없습니다.', style: TextStyle(color: Colors.grey, fontSize: 16)),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return EcoGlassScaffold(
      title: const Text('로봇 제어 기록'),
      builder: (context, topPadding, bottomPadding) {
        return ListenableBuilder(
          listenable: _controller,
          builder: (context, child) {
            if (_controller.isLoading && _controller.historyLogs.isEmpty) {
              return const Center(child: CircularProgressIndicator(color: AppColors.primary));
            }

            return RefreshIndicator(
              onRefresh: () => _controller.fetchHistoryLogs(widget.currentUserId),
              color: AppColors.primary,
              child: _controller.historyLogs.isEmpty
                  ? Stack(
                children: [
                  ListView(),
                  _buildEmptyState(),
                ],
              )
                  : ListView.builder(
                padding: EdgeInsets.only(top: topPadding, left: 16, right: 16, bottom: bottomPadding),
                itemCount: _controller.historyLogs.length,
                itemBuilder: (context, index) {
                  final log = _controller.historyLogs[index];
                  final rawCommand = log['command']?.toString() ?? '';
                  final rawTimestamp = log['timestamp']?.toString();
                  final zone = log['zone'] ?? '-';

                  // 🌟 3. 명령어 매핑 (start_patrol/start -> 동작, stop -> 정지, return_home -> 귀환)
                  String translatedCommand = '기타';
                  if (rawCommand == 'start_patrol' || rawCommand == 'start') {
                    translatedCommand = '동작';
                  } else if (rawCommand == 'stop') {
                    translatedCommand = '정지';
                  } else if (rawCommand == 'return_home' || rawCommand == 'home') {
                    translatedCommand = '귀환';
                  } else {
                    translatedCommand = rawCommand;
                  }

                  // 🌟 1. mm/dd 및 2. hh시 mm분 형식으로 타임스탬프 파싱
                  String formattedDate = '-';
                  String formattedTime = '-';
                  if (rawTimestamp != null && rawTimestamp.isNotEmpty) {
                    try {
                      final dt = DateTime.parse(rawTimestamp);
                      formattedDate = '${dt.month.toString().padLeft(2, '0')}/${dt.day.toString().padLeft(2, '0')}';
                      formattedTime = '${dt.hour.toString().padLeft(2, '0')}시 ${dt.minute.toString().padLeft(2, '0')}분';
                    } catch (_) {
                      formattedDate = rawTimestamp; // 파싱 실패 시 원본 유지
                    }
                  }

                  return Card(
                    elevation: 0, margin: const EdgeInsets.only(bottom: 12),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12), side: BorderSide(color: AppColors.primary.withValues(alpha: 0.1))),
                    child: ListTile(
                      leading: Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(color: AppColors.primary.withValues(alpha: 0.15), shape: BoxShape.circle),
                        child: const Icon(Icons.smart_toy_rounded, color: AppColors.primary),
                      ),
                      title: Text(' $translatedCommand', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                      subtitle: Text('구역: $zone  |  날짜: $formattedDate  |  시간: $formattedTime'),
                    ),
                  );
                },
              ),
            );
          },
        );
      },
    );
  }
}