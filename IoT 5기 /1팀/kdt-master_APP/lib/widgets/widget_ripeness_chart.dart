// lib/widgets/widget_ripeness_chart.dart
import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'dart:math' as math;
import '../models/app_models.dart';

class RipenessChartWidget extends StatelessWidget {
  final List<RipenessData> ripenessList;

  const RipenessChartWidget({super.key, required this.ripenessList});

  @override
  Widget build(BuildContext context) {
    if (ripenessList.isEmpty) return const Center(child: Text('집계된 데이터가 없습니다.', style: TextStyle(color: Colors.grey)));

    final double chartWidth = ripenessList.length * 60.0 > MediaQuery.of(context).size.width
        ? ripenessList.length * 60.0
        : MediaQuery.of(context).size.width - 32;

    // 🌟 동적으로 최대값(maxY) 계산 (오버플로우 방지)
    double maxVal = 80;
    for(var d in ripenessList) {
      double maxInItem = [d.unripeCount, d.ripeCount, d.overripeCount].reduce(math.max).toDouble();
      if (maxInItem + 20 > maxVal) maxVal = maxInItem + 20;
    }

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: SizedBox(
        width: chartWidth,
        child: BarChart(
          BarChartData(
            alignment: BarChartAlignment.spaceAround,
            maxY: maxVal,
            barTouchData: BarTouchData(enabled: true),
            gridData: const FlGridData(show: true, drawVerticalLine: false),
            titlesData: FlTitlesData(
              topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
              rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
              leftTitles: AxisTitles(
                sideTitles: SideTitles(
                  showTitles: true, reservedSize: 30,
                  getTitlesWidget: (v, m) => v % 20 != 0 ? const SizedBox.shrink() : Text('${v.toInt()}', style: const TextStyle(fontSize: 10, color: Colors.grey)),
                ),
              ),
              bottomTitles: AxisTitles(
                sideTitles: SideTitles(
                  showTitles: true,
                  getTitlesWidget: (double value, TitleMeta meta) {
                    int index = value.toInt();
                    if (index < 0 || index >= ripenessList.length) return const SizedBox.shrink();
                    return SideTitleWidget(axisSide: meta.axisSide, space: 8, child: Text(ripenessList[index].date, style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Colors.grey)));
                  },
                ),
              ),
            ),
            borderData: FlBorderData(show: true, border: Border(bottom: BorderSide(color: Colors.grey.shade400, width: 1))),
            barGroups: ripenessList.asMap().entries.map((entry) {
              int index = entry.key;
              RipenessData data = entry.value;
              return BarChartGroupData(
                x: index,
                barsSpace: 4,
                barRods: [
                  BarChartRodData(toY: data.unripeCount.toDouble(), color: Colors.green, width: 8, borderRadius: BorderRadius.circular(2)),
                  BarChartRodData(toY: data.ripeCount.toDouble(), color: Colors.redAccent, width: 8, borderRadius: BorderRadius.circular(2)),
                  BarChartRodData(toY: data.overripeCount.toDouble(), color: Colors.purple, width: 8, borderRadius: BorderRadius.circular(2)),
                ],
              );
            }).toList(),
          ),
        ),
      ),
    );
  }
}