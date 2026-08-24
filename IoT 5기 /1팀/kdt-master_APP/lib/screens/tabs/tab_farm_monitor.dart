// lib/screens/tabs/tab_farm_monitor.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/app_theme.dart';
import '../../providers/environment_provider.dart';
import '../../providers/auth_provider.dart';
import '../../providers/crop_provider.dart';
import '../../widgets/app_widgets.dart';
import '../../widgets/widget_farm_env_chart.dart';
import '../screen_fruit_dashboard.dart';

class TabFarmMonitor extends StatelessWidget {
  const TabFarmMonitor({super.key});

  @override
  Widget build(BuildContext context) {
    final double topPadding = kToolbarHeight + MediaQuery.of(context).padding.top + 16.0;
    final userName = context.watch<AuthProvider>().currentUser?.name ?? '사용자';
    final cropProvider = context.watch<CropProvider>();
    final envProvider = context.watch<EnvironmentProvider>();

    // 🌟 화면에 보여줄 때 비워진(삭제된) 작물은 제외한 activeCrops만 사용
    final activeFruits = cropProvider.activeCrops;

    return SingleChildScrollView(
      padding: EdgeInsets.only(top: topPadding, left: 16, right: 16, bottom: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Card(
            color: Colors.white, elevation: 0,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20), side: BorderSide(color: Colors.grey.shade200)),
            child: Padding(
              padding: const EdgeInsets.all(12.0),
              child: Text('반갑습니다, $userName님! 🌱', textAlign: TextAlign.center, style: const TextStyle(fontWeight: FontWeight.bold, color: AppColors.primary, fontSize: 16)),
            ),
          ),
          const SizedBox(height: 6),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  const Text('📊 온습도현황', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                  const SizedBox(width: 8),
                  RangeSelectButton(
                    label: '일', currentValue: envProvider.selectedRange, options: const [7, 14, 30, 60, 90],
                    onSelected: (val) => envProvider.setRange(val),
                  ),
                ],
              ),
              Row(children: const [
                Icon(Icons.circle, size: 8, color: AppColors.chartTemp), SizedBox(width: 4), Text('온도', style: TextStyle(fontSize: 11)), SizedBox(width: 8),
                Icon(Icons.circle, size: 8, color: AppColors.chartHumid), SizedBox(width: 4), Text('습도', style: TextStyle(fontSize: 11)),
              ])
            ],
          ),
          const SizedBox(height: 12),
          SizedBox(height: 400, child: FarmEnvChartWidget(envProvider: envProvider)),
          const SizedBox(height: 24),
          const Text('작물별 현황', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(height: 4),
          if (cropProvider.isLoading)
            const SizedBox(height: 150, child: Center(child: CircularProgressIndicator(color: AppColors.primary)))
          else
            GridView.builder(
              shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount: 2, childAspectRatio: 1.1, crossAxisSpacing: 12, mainAxisSpacing: 12),
              itemCount: activeFruits.length, // 🌟 activeFruits 개수만큼만 그림
              itemBuilder: (context, index) {
                final fruit = activeFruits[index];
                return ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.buttonBg, foregroundColor: AppColors.buttonText, elevation: 0,
                      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.only(topLeft: Radius.circular(24), bottomRight: Radius.circular(24), topRight: Radius.circular(8), bottomLeft: Radius.circular(8))),
                    ),
                    onPressed: () => Navigator.push(context, MaterialPageRoute(
                        builder: (context) => FruitDashboardScreen(
                          currentUserId: context.read<AuthProvider>().currentUser?.userId ?? '',
                          currentUserName: userName,
                          selectedFruitName: fruit.name,
                          selectedFruitIcon: fruit.icon,
                          selectedFruitCode: fruit.cropId,
                        )
                    )),
                    child: FittedBox(
                      fit: BoxFit.scaleDown,
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(fruit.icon, style: const TextStyle(fontSize: 40)),
                          const SizedBox(width: 8),
                          Text(fruit.name, style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
                        ],
                      ),
                    )
                );
              },
            ),
        ],
      ),
    );
  }
}
