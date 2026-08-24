// lib/screens/tabs/tab_robot_control.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../providers/robot_provider.dart';
import '../../providers/auth_provider.dart';
import '../../widgets/robot/robot_control_panel.dart';

class TabRobotControl extends StatefulWidget {
  const TabRobotControl({super.key});

  @override
  State<TabRobotControl> createState() => _TabRobotControlState();
}

class _TabRobotControlState extends State<TabRobotControl> with TickerProviderStateMixin {
  late AnimationController _waveController;
  late AnimationController _snapController;

  @override
  void initState() {
    super.initState();
    _waveController = AnimationController(vsync: this, duration: const Duration(seconds: 2))..repeat();
    _snapController = AnimationController(vsync: this, duration: const Duration(milliseconds: 500));
    _snapController.addListener(() {
      if (mounted) {
        context.read<RobotProvider>().updateSliderDragging(_snapController.value);
      }
    });
  }

  @override
  void dispose() {
    _waveController.dispose();
    _snapController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final double topPadding = kToolbarHeight + MediaQuery.of(context).padding.top + 16.0;
    final userId = context.watch<AuthProvider>().currentUser?.userId ?? '';

    return SingleChildScrollView(
      padding: EdgeInsets.only(top: topPadding, left: 16, right: 16, bottom: 24),
      child: RobotControlPanel(
        userId: userId,
        waveController: _waveController,
        snapController: _snapController,
      ),
    );
  }
}
