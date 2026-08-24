// lib/widgets/robot_path_map.dart
import 'package:flutter/material.dart';
import '../core/app_theme.dart';

class RobotPathMap extends StatelessWidget {
  final String currentZone;

  const RobotPathMap({super.key, required this.currentZone});

  @override
  Widget build(BuildContext context) {
    const double mapHeight = 110.0;
    const double markerWidth = 50.0;
    const double lineInset = 35.0;
    const double markerOffset = lineInset - (markerWidth / 2);

    return SizedBox(
      height: mapHeight,
      child: Stack(
        children: [
          Positioned(
            top: 25, bottom: 25, left: lineInset, right: lineInset,
            child: Container(
              decoration: BoxDecoration(
                border: Border(
                  left: BorderSide(color: Colors.grey.shade300, width: 4),
                  top: BorderSide(color: Colors.grey.shade300, width: 4),
                  right: BorderSide(color: Colors.grey.shade300, width: 4),
                ),
                borderRadius: const BorderRadius.only(topLeft: Radius.circular(20), topRight: Radius.circular(20)),
              ),
            ),
          ),
          Positioned(bottom: 0, left: markerOffset, child: _buildMarker('A1', currentZone)),
          Positioned(top: 0, left: 0, right: 0, child: Center(child: _buildMarker('A2', currentZone))),
          Positioned(bottom: 0, right: markerOffset, child: _buildMarker('A3', currentZone)),
        ],
      ),
    );
  }

  Widget _buildMarker(String zone, String currentZone) {
    bool isActive = zone.toLowerCase() == currentZone.toLowerCase();

    return SizedBox(
      width: 50,
      child: AnimatedScale(
        scale: isActive ? 1.2 : 1.0, duration: const Duration(milliseconds: 300), curve: Curves.easeOutBack,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            AnimatedContainer(
              duration: const Duration(milliseconds: 300), padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: isActive ? AppColors.primary : Colors.white, shape: BoxShape.circle,
                border: Border.all(color: isActive ? AppColors.primary : Colors.grey.shade400, width: 2),
                boxShadow: isActive ? [BoxShadow(color: AppColors.primary.withValues(alpha: 0.4), blurRadius: 8, spreadRadius: 2)] : [],
              ),
              child: Icon(Icons.smart_toy_rounded, color: isActive ? Colors.white : Colors.grey.shade400, size: 18),
            ),
            const SizedBox(height: 6),
            Text(zone, style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: isActive ? AppColors.primary : Colors.grey.shade500)),
          ],
        ),
      ),
    );
  }
}