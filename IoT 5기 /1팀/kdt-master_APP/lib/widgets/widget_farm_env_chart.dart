// lib/widgets/widget_farm_env_chart.dart
import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../providers/environment_provider.dart';
import '../core/app_constants.dart';

class FarmEnvChartWidget extends StatelessWidget {
  final EnvironmentProvider envProvider;
  const FarmEnvChartWidget({super.key, required this.envProvider});

  @override
  Widget build(BuildContext context) {
    if (envProvider.isLoading) return const Center(child: CircularProgressIndicator(color: Colors.green));
    if (envProvider.dailyLogs.isEmpty) return const Center(child: Text('데이터가 없습니다.'));

    final chartWidth = envProvider.dailyLogs.length * AppConstants.chartScrollWidthPerDay > MediaQuery.of(context).size.width
        ? envProvider.dailyLogs.length * AppConstants.chartScrollWidthPerDay
        : MediaQuery.of(context).size.width - 32;

    const double chartTotalHeight = 390.0;
    const double bottomAreaHeight = 35.0;
    const double topMargin = 15.0;
    const double gridHeight = chartTotalHeight - bottomAreaHeight - topMargin;

    final List<LineChartBarData> bars = [
      _line(envProvider.maxTempSpots, Colors.red, 2),
      _line(envProvider.minTempSpots, Colors.redAccent, 1.5),
      _line(envProvider.maxHumidSpots, Colors.blue, 2),
      _line(envProvider.minHumidSpots, Colors.blueAccent, 1.5),
    ];

    return Container(
      height: chartTotalHeight,
      padding: const EdgeInsets.only(bottom: 5),
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 45),
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: SizedBox(
                width: chartWidth,
                height: chartTotalHeight,
                child: LineChart(
                  LineChartData(
                    lineTouchData: LineTouchData(
                      enabled: false,
                      touchTooltipData: LineTouchTooltipData(
                        tooltipBgColor: Colors.transparent,
                        tooltipPadding: EdgeInsets.zero,
                        tooltipMargin: 2,
                        getTooltipItems: (spots) => spots.map((s) {
                          double val = s.y;
                          if (s.barIndex < 2) val /= AppConstants.tempScaleFactor;
                          return LineTooltipItem(val.toStringAsFixed(0), TextStyle(color: bars[s.barIndex].color, fontWeight: FontWeight.bold, fontSize: 8));
                        }).toList(),
                      ),
                    ),
                    // 🌟 Out of Bounds 방지: dailyLogs.length가 아닌 실제 spots.length 만큼 생성
                    showingTooltipIndicators: [
                      ...List.generate(bars.length, (barIdx) {
                        return List.generate(bars[barIdx].spots.length, (i) {
                          return ShowingTooltipIndicators([LineBarSpot(bars[barIdx], barIdx, bars[barIdx].spots[i])]);
                        });
                      }).expand((e) => e).toList(),
                    ],
                    minY: 0, maxY: 100,
                    gridData: FlGridData(
                      show: true, drawVerticalLine: true, verticalInterval: 1, horizontalInterval: 20, drawHorizontalLine: true,
                      getDrawingHorizontalLine: (v) => FlLine(color: Colors.grey.withValues(alpha: 0.15), strokeWidth: 1, dashArray: [5, 5]),
                      getDrawingVerticalLine: (v) => FlLine(color: Colors.grey.withValues(alpha: 0.1), strokeWidth: 0.5),
                    ),
                    titlesData: FlTitlesData(
                      topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                      leftTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                      rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                      bottomTitles: AxisTitles(sideTitles: SideTitles(showTitles: true, interval: 1, reservedSize: bottomAreaHeight, getTitlesWidget: (v, m) {
                        int i = v.toInt();
                        if (i < 0 || i >= envProvider.dates.length) return const SizedBox.shrink();
                        return SideTitleWidget(axisSide: m.axisSide, space: 10, child: Text(envProvider.dates[i], style: const TextStyle(fontSize: 9, color: Colors.grey, fontWeight: FontWeight.bold)));
                      })),
                    ),
                    borderData: FlBorderData(show: true, border: Border.all(color: Colors.grey.shade300)),
                    lineBarsData: bars,
                    betweenBarsData: [
                      BetweenBarsData(fromIndex: 0, toIndex: 1, color: Colors.red.withValues(alpha: 0.12)),
                      BetweenBarsData(fromIndex: 2, toIndex: 3, color: Colors.blue.withValues(alpha: 0.12)),
                    ],
                  ),
                ),
              ),
            ),
          ),
          Positioned(left: 0, top: topMargin, bottom: bottomAreaHeight, width: 40, child: _FixedAxis(isLeft: true, totalHeight: gridHeight)),
          Positioned(right: 0, top: topMargin, bottom: bottomAreaHeight, width: 40, child: _FixedAxis(isLeft: false, totalHeight: gridHeight)),
        ],
      ),
    );
  }

  LineChartBarData _line(List<FlSpot> s, Color c, double w) => LineChartBarData(spots: s, isCurved: true, color: c, barWidth: w, dotData: const FlDotData(show: true), belowBarData: BarAreaData(show: false));
}

class _FixedAxis extends StatelessWidget {
  final bool isLeft;
  final double totalHeight;
  const _FixedAxis({required this.isLeft, required this.totalHeight});

  @override
  Widget build(BuildContext context) {
    return Stack(
      clipBehavior: Clip.none,
      children: [
        Positioned(top: -15, left: isLeft ? 10 : 0, right: isLeft ? 0 : 10, child: Text(isLeft ? '%' : '°C', textAlign: isLeft?TextAlign.right:TextAlign.left, style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Colors.grey))),
        ...List.generate(6, (i) {
          double topPos = (i / 5) * totalHeight;
          int val = 100 - (i * 20);
          String label = isLeft ? '$val' : '${(val / AppConstants.tempScaleFactor).toInt()}';
          return Positioned(
            top: topPos - 6, left: 0, right: 0,
            child: Text(label, textAlign: isLeft ? TextAlign.right : TextAlign.left, style: TextStyle(fontSize: 10, color: isLeft ? Colors.blue.shade700 : Colors.red.shade700, fontWeight: FontWeight.bold)),
          );
        }),
      ],
    );
  }
}