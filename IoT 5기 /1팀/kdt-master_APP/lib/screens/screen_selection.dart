// lib/screens/screen_selection.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/auth_provider.dart';
import '../providers/crop_provider.dart';
import '../providers/environment_provider.dart';
import '../providers/alert_provider.dart';

import '../core/app_theme.dart';
import '../widgets/app_widgets.dart';
import 'screen_settings.dart';
import 'screen_calendar.dart';
import 'tabs/tab_farm_monitor.dart';
import 'tabs/tab_robot_control.dart';

class FruitSelectionScreen extends StatefulWidget {
  const FruitSelectionScreen({super.key});

  @override
  State<FruitSelectionScreen> createState() => _FruitSelectionScreenState();
}

class _FruitSelectionScreenState extends State<FruitSelectionScreen> {
  int _currentIndex = 0;
  bool _isInitialized = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_isInitialized) {
      final authProvider = context.read<AuthProvider>();
      final userId = authProvider.currentUser?.userId ?? '';

      if (userId.isNotEmpty) {
        _initializeGlobalData(userId);
        _isInitialized = true;
      }
    }
  }

  void _initializeGlobalData(String userId) async {
    final cropProvider = context.read<CropProvider>();
    final envProvider = context.read<EnvironmentProvider>();
    final alertProvider = context.read<AlertProvider>();

    await cropProvider.fetchCrops(userId);
    await cropProvider.preCalculateAllHarvest(userId);

    if (!mounted) return;

    envProvider.fetchEnvironmentLogs(userId);
    alertProvider.init(userId);
  }

  @override
  Widget build(BuildContext context) {
    final alertCount = context.watch<AlertProvider>().unreadAlertCount;

    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: GlassAppBar(
        title: const Text('스마트팜 통합 관제'),
        actions: [
          IconButton(
            icon: const Icon(Icons.calendar_month_rounded),
            onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (context) => const CalendarScreen())),
          ),
          IconButton(
            icon: const Icon(Icons.settings_rounded),
            // 🌟 설정 화면에서 돌아올 때(await) 최신 작물 데이터를 다시 불러와서 새로고침!
            onPressed: () async {
              final currentFruits = context.read<CropProvider>().crops;
              await Navigator.push(context, MaterialPageRoute(builder: (context) => SettingsScreen(currentFruits: currentFruits)));

              if (mounted) {
                final userId = context.read<AuthProvider>().currentUser?.userId ?? '';
                if (userId.isNotEmpty) {
                  await context.read<CropProvider>().fetchCrops(userId);
                  context.read<CropProvider>().preCalculateAllHarvest(userId);
                }
              }
            },
          ),
        ],
      ),
      body: IndexedStack(
        index: _currentIndex,
        children: const [
          TabFarmMonitor(),
          TabRobotControl(),
        ],
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (index) => setState(() => _currentIndex = index),
        selectedItemColor: AppColors.primary,
        unselectedItemColor: Colors.grey,
        backgroundColor: Colors.white,
        items: [
          BottomNavigationBarItem(
            icon: Stack(
              clipBehavior: Clip.none,
              children: [
                const Icon(Icons.dashboard_rounded),
                if (alertCount > 0)
                  Positioned(
                    right: -6, top: -4,
                    child: Container(
                      padding: const EdgeInsets.all(4),
                      decoration: const BoxDecoration(color: Colors.red, shape: BoxShape.circle),
                      child: Text(alertCount > 99 ? '99+' : '$alertCount', style: const TextStyle(color: Colors.white, fontSize: 8, fontWeight: FontWeight.bold)),
                    ),
                  ),
              ],
            ),
            label: '모니터링',
          ),
          const BottomNavigationBarItem(icon: Icon(Icons.smart_toy_rounded), label: '로봇 제어'),
        ],
      ),
    );
  }
}