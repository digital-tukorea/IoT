// lib/screens/screen_disease_alert_history.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/app_theme.dart';
import '../widgets/app_widgets.dart';
import '../providers/alert_provider.dart';

class ScreenDiseaseAlertHistory extends StatelessWidget {
  final String currentUserId;
  const ScreenDiseaseAlertHistory({super.key, required this.currentUserId});

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            padding: const EdgeInsets.all(32),
            decoration: const BoxDecoration(color: AppColors.alertCardBg, shape: BoxShape.circle),
            child: const Icon(Icons.inbox_rounded, size: 72, color: Colors.red),
          ),
          const SizedBox(height: 16),
          const Text('저장된 질병 진단 이력이 없습니다.', style: TextStyle(color: Colors.grey, fontSize: 16)),
        ],
      ),
    );
  }

  // 🌟 항목 터치 시 띄워주는 상세 다이얼로그
  void _showDetailDialog(BuildContext context, Map<String, dynamic> log, String date, String time) {
    final message = log['message'] ?? '이상 증상 감지';
    final zone = log['zone'] ?? '-';
    final status = log['health_status'] ?? '경고';
    final imageUrl = log['image_url']?.toString();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text('상세 진단 정보', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18, color: Colors.red)),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (imageUrl != null && imageUrl.isNotEmpty) ...[
                ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: Image.network(
                    imageUrl, width: double.infinity, fit: BoxFit.cover,
                    errorBuilder: (c, e, s) => Container(height: 150, color: Colors.grey.shade200, child: const Center(child: Text('이미지를 불러올 수 없습니다.', style: TextStyle(color: Colors.grey)))),
                  ),
                ),
                const SizedBox(height: 16),
              ],
              Text('• 발생 구역: $zone', style: const TextStyle(fontSize: 15)),
              const SizedBox(height: 4),
              Text('• 진단 상태: $status', style: const TextStyle(fontSize: 15)),
              const SizedBox(height: 4),
              Text('• 발생 일시: $date $time', style: const TextStyle(fontSize: 15)),
              const Divider(height: 24),
              Text('메시지: $message', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: Colors.black87)),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('확인', style: TextStyle(fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final alertProvider = context.watch<AlertProvider>();
    final connected = alertProvider.isConnected;
    final diseaseLogs = alertProvider.alertLogs;

    return EcoGlassScaffold(
      title: const Text('AI 비전 진단 질병 경고 이력'),
      actions: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16.0),
          child: Row(
            children: [
              Icon(Icons.circle, size: 10, color: connected ? Colors.green : Colors.red),
              const SizedBox(width: 4),
              Text(connected ? '실시간 수신중' : '수신 대기중', style: const TextStyle(fontSize: 10)),
            ],
          ),
        )
      ],
      builder: (context, topPadding, bottomPadding) {
        return diseaseLogs.isEmpty
            ? Stack(children: [ListView(), _buildEmptyState()])
            : ListView.builder(
          padding: EdgeInsets.only(top: topPadding, left: 16, right: 16, bottom: bottomPadding),
          itemCount: diseaseLogs.length,
          itemBuilder: (context, index) {
            final log = diseaseLogs[index];
            final isRead = log['isRead'] == true;
            final zone = log['zone'] ?? '-';

            // 날짜 포맷팅
            final rawTimestamp = log['timestamp']?.toString();
            String formattedDate = '-';
            String formattedTime = '';
            if (rawTimestamp != null && rawTimestamp.isNotEmpty) {
              try {
                final dt = DateTime.parse(rawTimestamp);
                formattedDate = '${dt.month.toString().padLeft(2, '0')}/${dt.day.toString().padLeft(2, '0')}';
                formattedTime = '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
              } catch (_) {
                formattedDate = rawTimestamp;
              }
            }

            return Card(
              margin: const EdgeInsets.only(bottom: 12), elevation: 0,
              // 🌟 안 읽은 상태면 연한 빨간색 테두리, 읽었으면 회색 테두리
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12), side: BorderSide(color: isRead ? Colors.grey.shade300 : Colors.red.withValues(alpha: 0.3), width: isRead ? 1 : 1.5)),
              child: ListTile(
                contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                // 🌟 터치 시 읽음 처리 및 상세 다이얼로그 호출
                onTap: () {
                  context.read<AlertProvider>().markAlertAsRead(log);
                  _showDetailDialog(context, log, formattedDate, formattedTime);
                },
                leading: Icon(Icons.warning_amber_rounded, color: isRead ? Colors.grey.shade400 : Colors.red, size: 28),
                // 🌟 기획에 맞게 리스트에서는 구역과 날짜만 노출
                title: Text('발생 구역: $zone', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: isRead ? Colors.grey.shade700 : Colors.black87)),
                subtitle: Padding(padding: const EdgeInsets.only(top: 4.0), child: Text('날짜: $formattedDate $formattedTime', style: TextStyle(color: isRead ? Colors.grey.shade600 : Colors.black87))),
                // 안 읽은 항목에만 빨간 점(Dot) 표시
                trailing: isRead ? null : const Icon(Icons.circle, color: Colors.redAccent, size: 10),
              ),
            );
          },
        );
      },
    );
  }
}