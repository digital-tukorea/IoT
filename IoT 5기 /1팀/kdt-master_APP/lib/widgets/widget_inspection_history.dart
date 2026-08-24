// lib/widgets/widget_inspection_history.dart
import 'package:flutter/material.dart';
import '../core/app_theme.dart';

class InspectionHistoryWidget extends StatelessWidget {
  final List<Map<String, dynamic>> logs;

  const InspectionHistoryWidget({super.key, required this.logs});

  // 🌟 사진 확대 팝업을 띄우는 헬퍼 함수
  void _showImageDialog(BuildContext context, String imageUrl) {
    showDialog(
      context: context,
      builder: (context) => Dialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        clipBehavior: Clip.antiAlias,
        backgroundColor: Colors.transparent, // 배경을 투명하게 처리
        child: Stack(
          alignment: Alignment.center,
          children: [
            Image.network(
              imageUrl,
              fit: BoxFit.contain,
              errorBuilder: (context, error, stackTrace) => Container(
                height: 200,
                width: double.infinity,
                color: Colors.white,
                child: const Center(child: Text('이미지를 불러올 수 없습니다.', style: TextStyle(color: Colors.grey))),
              ),
            ),
            Positioned(
              top: 8,
              right: 8,
              child: IconButton(
                icon: const Icon(Icons.close_rounded, color: Colors.white, size: 28, shadows: [Shadow(color: Colors.black87, blurRadius: 4)]),
                onPressed: () => Navigator.pop(context),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (logs.isEmpty) return const Center(child: Text('조회 이력이 없습니다.', style: TextStyle(color: Colors.grey)));

    return ListView.builder(
      padding: EdgeInsets.zero,
      itemCount: logs.length,
      itemBuilder: (context, index) {
        final log = logs[index];

        // 🌟 상태값 처리
        final rawStatus = log['health_status'];
        final isAlert = rawStatus == '경고' || rawStatus == '위험';
        String displayStatus = rawStatus ?? 'Normal';
        if (displayStatus == '정상') displayStatus = 'Normal';

        // 🌟 날짜 및 시간 포맷팅
        final rawTimestamp = log['timestamp']?.toString();
        String formattedDate = '-';
        String formattedTime = '-';

        if (rawTimestamp != null && rawTimestamp.isNotEmpty) {
          try {
            final dt = DateTime.parse(rawTimestamp);
            formattedDate = '${dt.month.toString().padLeft(2, '0')}/${dt.day.toString().padLeft(2, '0')}';
            formattedTime = '${dt.hour.toString().padLeft(2, '0')}시 ${dt.minute.toString().padLeft(2, '0')}분';
          } catch (_) {
            formattedDate = rawTimestamp;
            formattedTime = '';
          }
        }

        // 이미지 유무 확인
        final imageUrl = log['image_url']?.toString();
        final hasImage = imageUrl != null && imageUrl.isNotEmpty;

        return Card(
          elevation: 0, color: Colors.white, margin: const EdgeInsets.symmetric(vertical: 4),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12), side: BorderSide(color: isAlert ? Colors.red.shade200 : Colors.grey.shade200)),
          child: ListTile(
            // 🌟 3. 항목 터치 시 이미지 팝업 또는 스낵바 알림 실행
            onTap: () {
              if (hasImage) {
                _showImageDialog(context, imageUrl);
              } else {
                ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('📷 등록된 사진이 없습니다.'), duration: Duration(seconds: 1)));
              }
            },
            leading: hasImage
                ? ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: Image.network(imageUrl, width: 50, height: 50, fit: BoxFit.cover, errorBuilder: (context, error, stackTrace) => Container(width:50, height:50, color:Colors.grey.shade300, child: const Icon(Icons.broken_image, size:20, color:Colors.grey))),
            )
                : Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(color: isAlert ? Colors.red.withValues(alpha: 0.15) : AppColors.primary.withValues(alpha: 0.15), shape: BoxShape.circle),
              child: Icon(isAlert ? Icons.warning_amber_rounded : Icons.check_circle_outline_rounded, color: isAlert ? Colors.red : AppColors.primary),
            ),
            title: Text('상태: $displayStatus', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: isAlert ? Colors.red.shade700 : Colors.black87)),
            subtitle: Text('구역: ${log['zone'] ?? '-'}  |  날짜: $formattedDate  |  시간: $formattedTime'),
            // 🌟 사진이 있는 경우 돋보기 아이콘을 우측에 띄워 터치 가능함을 유도
            trailing: hasImage ? const Icon(Icons.zoom_in_rounded, color: Colors.grey, size: 20) : null,
          ),
        );
      },
    );
  }
}