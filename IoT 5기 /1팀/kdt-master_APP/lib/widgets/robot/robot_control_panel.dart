// lib/widgets/robot/robot_control_panel.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/app_theme.dart';
import '../../providers/robot_provider.dart';
import '../../screens/screen_robot_history.dart';
import '../custom_slider_thumb.dart';
import '../robot_path_map.dart';

class RobotControlPanel extends StatelessWidget {
  final String userId;
  final AnimationController waveController;
  final AnimationController snapController;

  const RobotControlPanel({
    super.key,
    required this.userId,
    required this.waveController,
    required this.snapController,
  });

  @override
  Widget build(BuildContext context) {
    // 🌟 전체 Card 리빌드를 막기 위해 Consumer 제거하고 개별 Selector 위임
    return Card(
      color: AppColors.robotPanelBg, elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _ControlPanelHeader(userId: userId),
            const SizedBox(height: 24),
            Selector<RobotProvider, String>(
              selector: (_, provider) => provider.currentZone,
              builder: (_, zone, __) => RobotPathMap(currentZone: zone),
            ),
            const SizedBox(height: 16),
            _RobotControlSlider(
              userId: userId,
              waveController: waveController,
              snapController: snapController,
            ),
            const SizedBox(height: 8),
            Selector<RobotProvider, String>(
              selector: (_, provider) => provider.currentZone,
              builder: (_, zone, __) => _LocationStatus(zone: zone),
            ),
          ],
        ),
      ),
    );
  }
}

class _ControlPanelHeader extends StatelessWidget {
  final String userId;
  const _ControlPanelHeader({required this.userId});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        const Flexible(
          child: FittedBox(
            fit: BoxFit.scaleDown, alignment: Alignment.centerLeft,
            child: Row(children: [
              Icon(Icons.smart_toy_rounded, color: AppColors.primary), SizedBox(width: 8),
              Text('로봇 제어 패널', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppColors.buttonText)),
            ]),
          ),
        ),
        const SizedBox(width: 8),
        FittedBox(
          fit: BoxFit.scaleDown, alignment: Alignment.centerRight,
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(backgroundColor: Colors.white, foregroundColor: AppColors.primary, elevation: 0, padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8), side: const BorderSide(color: AppColors.primary, width: 1.0), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16))),
                onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (context) => RobotHistoryScreen(currentUserId: userId))),
                icon: const Icon(Icons.history_rounded, size: 18), label: const Text('기록', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
              ),
              const SizedBox(width: 8),
              Selector<RobotProvider, bool>(
                selector: (_, provider) => provider.isReturningHome,
                builder: (context, isReturning, _) {
                  return ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(backgroundColor: Colors.white, foregroundColor: AppColors.linkText, elevation: 0, padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8), side: const BorderSide(color: AppColors.linkText, width: 1.0), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16))),
                    onPressed: isReturning ? null : () => context.read<RobotProvider>().sendReturnCommand(userId, 'R001'),
                    icon: isReturning ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.linkText)) : const Icon(Icons.home_rounded, size: 18),
                    label: Text(isReturning ? '복귀 중...' : '귀환', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                  );
                },
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _RobotControlSlider extends StatelessWidget {
  final String userId;
  final AnimationController waveController;
  final AnimationController snapController;
  const _RobotControlSlider({required this.userId, required this.waveController, required this.snapController});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 100,
      child: AnimatedBuilder(
          animation: waveController,
          builder: (context, child) {
            return Selector<RobotProvider, double>(
                selector: (_, p) => p.sliderValue,
                builder: (context, sliderValue, _) {
                  return SliderTheme(
                    data: SliderTheme.of(context).copyWith(
                      trackHeight: 60.0, overlayShape: SliderComponentShape.noOverlay, showValueIndicator: ShowValueIndicator.never,
                      trackShape: StreamFlowTrackShape(waveAnimation: waveController),
                      thumbShape: StreamPebbleThumbShape(value: sliderValue, thumbRadius: 24.0),
                    ),
                    child: Slider(
                      value: sliderValue, min: 0.0, max: 1.0,
                      onChanged: (value) => context.read<RobotProvider>().updateSliderDragging(value),
                      onChangeEnd: (value) {
                        double targetValue = value >= 0.5 ? 1.0 : 0.0;
                        snapController.value = value;
                        snapController.animateTo(targetValue, curve: Curves.easeOutCubic).then((_) {
                          context.read<RobotProvider>().updateSliderEnd(targetValue, userId, 'R001');
                        });
                      },
                    ),
                  );
                }
            );
          }),
    );
  }
}

class _LocationStatus extends StatelessWidget {
  final String zone;
  const _LocationStatus({required this.zone});
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.circle, color: Colors.green, size: 16), const SizedBox(width: 8),
          const Text('현재 위치: ', style: TextStyle(fontSize: 14, color: AppColors.inputLabel, fontWeight: FontWeight.bold)), const SizedBox(width: 4),
          Text(zone.toUpperCase(), style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppColors.primary)),
        ],
      ),
    );
  }
}