import 'package:flutter/material.dart';

class CalendarLegend extends StatelessWidget {
  const CalendarLegend({super.key});

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 12,
      runSpacing: 8,
      alignment: WrapAlignment.center,
      children: [
        _dotLegend(Colors.amber, '질병'),
        _dotLegend(Colors.red, '온도'),
        _dotLegend(Colors.blue, '습도'),
        _dotLegend(Colors.orange, '수확'),
      ],
    );
  }

  Widget _dotLegend(Color c, String t) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(width: 8, height: 8, decoration: BoxDecoration(color: c, shape: BoxShape.circle)),
        const SizedBox(width: 4),
        Text(t, style: const TextStyle(fontSize: 11, color: Colors.grey)),
      ],
    );
  }
}
