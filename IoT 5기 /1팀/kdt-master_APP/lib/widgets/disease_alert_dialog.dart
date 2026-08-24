import 'package:flutter/material.dart';

/// 🚨 병충해 감지 알림 다이얼로그 (분리된 위젯)
class DiseaseAlertDialog extends StatelessWidget {
  final Map<String, dynamic> alertData;
  final String fallbackFruitName;

  const DiseaseAlertDialog({
    super.key,
    required this.alertData,
    required this.fallbackFruitName,
  });

  /// 팝업창을 간편하게 띄우기 위한 static 헬퍼 함수
  static Future<void> show(
      BuildContext context, {
        required Map<String, dynamic> alertData,
        required String fallbackFruitName,
      }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (BuildContext context) {
        return DiseaseAlertDialog(
          alertData: alertData,
          fallbackFruitName: fallbackFruitName,
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final imageUrl = alertData['image_url']?.toString();

    return AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      title: const Row(
        children: [
          Icon(Icons.warning_amber_rounded, color: Colors.red, size: 28),
          SizedBox(width: 8),
          Text(
            '🚨 병충해 감지 경고',
            style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold),
          ),
        ],
      ),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              alertData['message'] ?? '구역에서 문제가 발견되었습니다!',
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
            ),
            const SizedBox(height: 8),
            Text('• 발생 구역: ${alertData['zone'] ?? '-'}'),
            Text('• 로봇 ID: ${alertData['robot_id'] ?? '-'}'),
            Text('• 작물 구획: ${alertData['crop'] ?? fallbackFruitName}'),
            Text('• 생육 상태: ${alertData['growth_status'] ?? '-'}'),
            const SizedBox(height: 12),

            // S3 등에 업로드된 이미지 URL 표시
            if (imageUrl != null && imageUrl.isNotEmpty) ...[
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: Image.network(
                  imageUrl,
                  height: 180,
                  width: double.infinity,
                  fit: BoxFit.cover,
                  errorBuilder: (context, error, stackTrace) => Container(
                    height: 100,
                    color: Colors.grey.shade300,
                    child: const Center(child: Text('이미지를 불러올 수 없습니다.')),
                  ),
                  loadingBuilder: (context, child, loadingProgress) {
                    if (loadingProgress == null) return child;
                    return Container(
                      height: 150,
                      color: Colors.grey.shade100,
                      child: const Center(child: CircularProgressIndicator()),
                    );
                  },
                ),
              ),
            ],
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text(
            '확인',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
          ),
        ),
      ],
    );
  }
}