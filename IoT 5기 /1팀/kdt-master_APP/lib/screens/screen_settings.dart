// lib/screens/settings_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/app_theme.dart';
import '../widgets/app_widgets.dart';
import 'screen_crop_edit.dart';
import 'screen_login.dart';
import '../models/app_models.dart';
import '../providers/auth_provider.dart';
import '../services/service_mqtt.dart';

class SettingsScreen extends StatefulWidget {
  final List<CropModel> currentFruits;
  const SettingsScreen({super.key, required this.currentFruits});
  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late List<CropModel> _currentFruits;

  @override
  void initState() {
    super.initState();
    _currentFruits = List.from(widget.currentFruits);
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) {
        if (didPop) return;
        Navigator.pop(context, _currentFruits);
      },
      child: EcoGlassScaffold(
        title: const Text('농장 설정'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_rounded),
          onPressed: () => Navigator.pop(context, _currentFruits),
        ),
        builder: (context, topPadding, bottomPadding) {
          return ListView(
            padding: EdgeInsets.only(top: topPadding, bottom: bottomPadding),
            children: [
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
                child: Text('일반 설정', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: AppColors.primary)),
              ),
              ListTile(
                leading: Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(color: AppColors.primary.withValues(alpha: 0.15), shape: BoxShape.circle),
                  child: const Icon(Icons.local_florist_rounded, color: AppColors.primary, size: 24),
                ),
                title: const Text('작물 등록', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                subtitle: const Text('대시보드에 표시될 작물 이름과 아이콘 변경'),
                trailing: const Icon(Icons.chevron_right_rounded, color: Colors.grey),
                onTap: () async {
                  final updatedFruits = await Navigator.push(context, MaterialPageRoute(builder: (context) => CropEditScreen(currentFruits: _currentFruits)));
                  if (updatedFruits != null && updatedFruits is List<CropModel>) {
                    setState(() => _currentFruits = updatedFruits);
                  }
                },
              ),
              const Divider(height: 1),
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
                child: Text('계정 관리', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.redAccent)),
              ),
              ListTile(
                leading: Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(color: Colors.red.withValues(alpha: 0.1), shape: BoxShape.circle),
                  child: const Icon(Icons.logout_rounded, color: Colors.redAccent, size: 24),
                ),
                title: const Text('로그아웃', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.redAccent)),
                subtitle: const Text('현재 계정의 연결을 종료하고 로그인 화면으로 이동'),
                onTap: () => _showLogoutDialog(context),
              ),
              const Divider(height: 1),
            ],
          );
        },
      ),
    );
  }

  void _showLogoutDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('로그아웃'),
        content: const Text('정말 로그아웃 하시겠습니까?\n모든 실시간 연결이 종료됩니다.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('취소', style: TextStyle(color: Colors.grey)),
          ),
          TextButton(
            onPressed: () async {
              // 1. MQTT 연결 종료
              MqttService().disconnect();
              // 2. AuthProvider 로그아웃 (로컬 저장 데이터 삭제)
              await context.read<AuthProvider>().logout();
              
              if (!context.mounted) return;
              
              // 3. 로그인 화면으로 이동 및 스택 초기화
              Navigator.pushAndRemoveUntil(
                context,
                MaterialPageRoute(builder: (context) => const LoginScreen()),
                (route) => false,
              );
            },
            child: const Text('로그아웃', style: TextStyle(color: Colors.redAccent, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }
}