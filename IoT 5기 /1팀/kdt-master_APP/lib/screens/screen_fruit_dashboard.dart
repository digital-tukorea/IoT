// lib/screens/screen_fruit_dashboard.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/app_theme.dart';
import '../widgets/app_widgets.dart';
import '../widgets/widget_ripeness_chart.dart';
import '../widgets/widget_inspection_history.dart';
import '../controllers/controller_fruit_dashboard.dart';
import '../providers/crop_provider.dart';
import '../providers/alert_provider.dart';
import 'screen_disease_alert_history.dart';

class FruitDashboardScreen extends StatefulWidget {
  final String currentUserId, currentUserName, selectedFruitName, selectedFruitIcon, selectedFruitCode;
  const FruitDashboardScreen({super.key, required this.currentUserId, required this.currentUserName, required this.selectedFruitName, required this.selectedFruitIcon, required this.selectedFruitCode});
  @override
  State<FruitDashboardScreen> createState() => _FruitDashboardScreenState();
}

class _FruitDashboardScreenState extends State<FruitDashboardScreen> {
  late FruitDashboardController _dashboardController;

  @override
  void initState() {
    super.initState();
    _dashboardController = FruitDashboardController(
      userId: widget.currentUserId,
      fruitCode: widget.selectedFruitCode,
      cropProvider: Provider.of<CropProvider>(context, listen: false),
    );
  }

  @override
  void dispose() {
    _dashboardController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final alertProvider = context.watch<AlertProvider>();

    return EcoGlassScaffold(
      title: FittedBox(fit: BoxFit.scaleDown, child: Text('${widget.selectedFruitIcon} ${widget.selectedFruitName} 대시보드')),
      actions: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16.0),
          child: Row(children: [
            Icon(Icons.circle, size: 12, color: alertProvider.isConnected ? Colors.green : Colors.red),
            const SizedBox(width: 6),
            Text(alertProvider.isConnected ? 'MQTT 연결됨' : '연결 끊김', style: const TextStyle(fontSize: 12)),
          ]),
        )
      ],
      builder: (context, topPadding, bottomPadding) {
        return Padding(
          padding: EdgeInsets.only(top: topPadding, left: 16, right: 16, bottom: bottomPadding),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Card(
                color: AppColors.alertCardBg, elevation: 0,
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Row(
                    children: [
                      Flexible(flex: 1, child: FittedBox(fit: BoxFit.scaleDown, child: Text(widget.selectedFruitIcon, style: const TextStyle(fontSize: 32)))),
                      const SizedBox(width: 12),
                      Expanded(
                        flex: 4,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            FittedBox(fit: BoxFit.scaleDown, alignment: Alignment.centerLeft, child: Text('${widget.selectedFruitName} 실시간 모니터링', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold))),
                            FittedBox(fit: BoxFit.scaleDown, alignment: Alignment.centerLeft, child: Text('사용자: ${widget.currentUserName}', style: const TextStyle(fontSize: 12, color: Colors.black54))),
                          ],
                        ),
                      ),
                      const SizedBox(width: 8),
                      ElevatedButton.icon(
                        style: ElevatedButton.styleFrom(backgroundColor: Colors.white, foregroundColor: Colors.red.shade700, padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8), side: BorderSide(color: Colors.red.shade300, width: 1.0), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16))),
                        onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (context) => ScreenDiseaseAlertHistory(currentUserId: widget.currentUserId))),
                        icon: const Icon(Icons.warning_amber_rounded, size: 18),
                        // 🌟 전체 개수가 아닌 읽지 않은(unread) 알림 개수만 표시하도록 변경
                        label: Text('${alertProvider.unreadAlertCount}건', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      const Text('📊 생육 비율', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                      const SizedBox(width: 8),
                      ListenableBuilder(
                        listenable: _dashboardController,
                        builder: (context, _) => RangeSelectButton(
                          label: '일', currentValue: _dashboardController.selectedRange, options: const [7, 14, 30, 60],
                          onSelected: (val) => _dashboardController.setRange(val),
                        ),
                      ),
                    ],
                  ),
                  Row(children: const [
                    Icon(Icons.square, size: 10, color: Colors.green), SizedBox(width: 2), Text('미숙', style: TextStyle(fontSize: 11)), SizedBox(width: 4),
                    Icon(Icons.square, size: 10, color: Colors.redAccent), SizedBox(width: 2), Text('적숙', style: TextStyle(fontSize: 11)), SizedBox(width: 4),
                    Icon(Icons.square, size: 10, color: Colors.purple), SizedBox(width: 2), Text('과숙', style: TextStyle(fontSize: 11)),
                  ])
                ],
              ),
              const SizedBox(height: 12),
              SizedBox(
                height: 220,
                child: ListenableBuilder(
                  listenable: _dashboardController,
                  builder: (context, _) => RipenessChartWidget(ripenessList: _dashboardController.ripenessList),
                ),
              ),
              const SizedBox(height: 20),
              const Text('📸 작물 조회 이력', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),
              Expanded(child: InspectionHistoryWidget(logs: alertProvider.inspectionLogs)),
            ],
          ),
        );
      },
    );
  }
}
