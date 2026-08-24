// lib/widgets/calendar/calendar_day_tile.dart
import 'package:flutter/material.dart';
import '../../core/app_theme.dart';
import '../../core/app_constants.dart';
import '../../providers/environment_provider.dart';

class CalendarDayTile extends StatelessWidget {
  final DateTime date;
  final EnvDailyData? env;
  final String? harvestIcon, note;
  final bool hasDisease, isCurrentMonth, isToday;
  final VoidCallback onTap;

  const CalendarDayTile({
    super.key,
    required this.date,
    this.env,
    this.harvestIcon,
    this.note,
    required this.hasDisease,
    required this.isCurrentMonth,
    required this.isToday,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final bool isTempHigh = env != null && env!.maxTemp >= AppConstants.tempHighLimit;
    final bool isTempLow = env != null && env!.minTemp <= AppConstants.tempLowLimit;
    final bool isHumidHigh = env != null && env!.maxHumid >= AppConstants.humidHighLimit;
    final bool isHumidLow = env != null && env!.minHumid <= AppConstants.humidLowLimit;

    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: isToday ? AppColors.primary.withValues(alpha: 0.1) : Colors.grey.shade50,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: isToday ? AppColors.primary : Colors.grey.shade200, width: isToday ? 1.5 : 1),
        ),
        child: Opacity(
          opacity: isCurrentMonth ? 1 : 0.3,
          child: Stack(
            children: [
              Positioned(top: 4, left: 4, child: Text('${date.day}', style: const TextStyle(fontSize: 9, fontWeight: FontWeight.normal))),
              if (harvestIcon != null) Positioned(top: 4, right: 4, child: Text(harvestIcon!, style: const TextStyle(fontSize: 10))),

              // 🌟 Expanded 에러 방지: Positioned로 상하단 명시적 여백 제공하여 영역 강제 고정
              Positioned(
                top: 14, bottom: 12, left: 2, right: 2,
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        if (isTempHigh) const Text('🌡️↑', style: TextStyle(fontSize: 7.5, color: Colors.red, fontWeight: FontWeight.bold)),
                        if (isTempHigh && isHumidHigh) const SizedBox(width: 2),
                        if (isHumidHigh) const Text('💧↑', style: TextStyle(fontSize: 7.5, color: Colors.blue, fontWeight: FontWeight.bold)),
                      ],
                    ),
                    if (note != null && note!.isNotEmpty)
                      Flexible( // Expanded 대신 Flexible 사용
                        child: Text(
                          note!, textAlign: TextAlign.center, maxLines: 2, overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: 8.5, color: Colors.black87, fontWeight: FontWeight.w600),
                        ),
                      ),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        if (isTempLow) const Text('🌡️↓', style: TextStyle(fontSize: 7.5, color: Colors.red, fontWeight: FontWeight.bold)),
                        if (isTempLow && isHumidLow) const SizedBox(width: 2),
                        if (isHumidLow) const Text('💧↓', style: TextStyle(fontSize: 7.5, color: Colors.blue, fontWeight: FontWeight.bold)),
                      ],
                    ),
                  ],
                ),
              ),
              Positioned(
                bottom: 2, left: 0, right: 0,
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    if (hasDisease) _dot(3, Colors.amber),
                    if (harvestIcon != null) ...[
                      if (hasDisease) const SizedBox(width: 1),
                      _dot(3, Colors.orange),
                    ]
                  ],
                ),
              )
            ],
          ),
        ),
      ),
    );
  }

  Widget _dot(double s, Color c) => Container(
    width: s, height: s, margin: const EdgeInsets.symmetric(horizontal: 0.5),
    decoration: BoxDecoration(color: c, shape: BoxShape.circle),
  );
}