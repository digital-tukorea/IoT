// lib/screens/screen_calendar.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../widgets/app_widgets.dart';
import '../widgets/calendar/calendar_day_tile.dart';
import '../widgets/calendar/calendar_legend.dart';
import '../core/app_theme.dart';
import '../providers/crop_provider.dart';
import '../providers/environment_provider.dart';
import '../providers/alert_provider.dart';

class CalendarScreen extends StatefulWidget {
  const CalendarScreen({super.key});
  @override
  State<CalendarScreen> createState() => _CalendarScreenState();
}

class _CalendarScreenState extends State<CalendarScreen> {
  DateTime _displayDate = DateTime.now();

  void _moveMonth(int delta) => setState(() => _displayDate = DateTime(_displayDate.year, _displayDate.month + delta, 1));

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    final firstDay = DateTime(_displayDate.year, _displayDate.month, 1);
    final offset = firstDay.weekday % 7;

    return Consumer3<EnvironmentProvider, AlertProvider, CropProvider>(
      builder: (context, envP, alertP, cropP, _) {
        final diseaseSet = alertP.alertLogs.map((l) => (l['timestamp'] ?? '').toString().split(' ')[0]).toSet();
        final harvestMap = <String, String>{};
        cropP.harvestPeriods.forEach((_, range) {
          for (int i = 0; i <= range.end.difference(range.start).inDays; i++) {
            final d = range.start.add(Duration(days: i));
            harvestMap['${d.year}-${d.month.toString().padLeft(2,'0')}-${d.day.toString().padLeft(2,'0')}'] = range.fruitIcon;
          }
        });

        return EcoGlassScaffold(
          title: const Text('농장 활동 캘린더'),
          builder: (ctx, top, bottom) => SingleChildScrollView(
            padding: EdgeInsets.only(top: top, left: 10, right: 10, bottom: bottom),
            child: Column(
              children: [
                Card(
                  color: Colors.white, elevation: 0,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20), side: BorderSide(color: Colors.grey.shade200)),
                  child: Padding(
                    padding: const EdgeInsets.all(12.0),
                    child: Column(
                      children: [
                        _buildMonthHeader(),
                        const SizedBox(height: 16),
                        _buildWeekdayRow(),
                        const Divider(),
                        GridView.builder(
                          shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
                          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount: 7, mainAxisSpacing: 4, crossAxisSpacing: 4, childAspectRatio: 0.72),
                          itemCount: 42,
                          itemBuilder: (ctx, i) {
                            final date = firstDay.add(Duration(days: i - offset));
                            final ymd = '${date.year}-${date.month.toString().padLeft(2,'0')}-${date.day.toString().padLeft(2,'0')}';
                            final md = '${date.month.toString().padLeft(2,'0')}/${date.day.toString().padLeft(2,'0')}';
                            return CalendarDayTile(
                              key: ValueKey('tile_$ymd'),
                              date: date, env: envP.dailyMap[md], harvestIcon: harvestMap[ymd], hasDisease: diseaseSet.contains(ymd),
                              isCurrentMonth: date.month == _displayDate.month, isToday: date.year == now.year && date.month == now.month && date.day == now.day,
                              note: envP.getNoteForDate(ymd),
                              onTap: () => _showNoteDialog(context, date, envP.dailyMap[md], envP, ymd),
                            );
                          },
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                const CalendarLegend(),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildMonthHeader() => Row(
    mainAxisAlignment: MainAxisAlignment.spaceBetween,
    children: [
      IconButton(icon: const Icon(Icons.chevron_left), onPressed: () => _moveMonth(-1)),
      Text('${_displayDate.year}년 ${_displayDate.month}월', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18, color: AppColors.primary)),
      IconButton(icon: const Icon(Icons.chevron_right), onPressed: () => _moveMonth(1)),
    ],
  );

  Widget _buildWeekdayRow() {
    const days = ['일', '월', '화', '수', '목', '금', '토'];
    return Row(children: List.generate(7, (i) => Expanded(child: Center(child: Text(days[i], style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: i==0?Colors.red:(i==6?Colors.blue:Colors.grey)))))));
  }

  // 🌟 StatefulWidget을 가진 별도의 다이얼로그 호출
  void _showNoteDialog(BuildContext context, DateTime date, EnvDailyData? env, EnvironmentProvider provider, String ymd) {
    showDialog(
      context: context,
      builder: (ctx) => _NoteDialogWidget(date: date, env: env, provider: provider, ymd: ymd),
    );
  }
}

// 🌟 읽기/수정 모드 관리를 위한 Stateful 다이얼로그 위젯
class _NoteDialogWidget extends StatefulWidget {
  final DateTime date;
  final EnvDailyData? env;
  final EnvironmentProvider provider;
  final String ymd;
  const _NoteDialogWidget({required this.date, this.env, required this.provider, required this.ymd});

  @override
  State<_NoteDialogWidget> createState() => _NoteDialogWidgetState();
}

class _NoteDialogWidgetState extends State<_NoteDialogWidget> {
  late TextEditingController _controller;
  bool _isEditing = false;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: widget.provider.getNoteForDate(widget.ymd));
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Widget _row(String l, String v, Color c) => Padding(padding: const EdgeInsets.symmetric(vertical: 2), child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [Text(l, style: const TextStyle(fontSize: 12)), Text(v, style: TextStyle(color: c, fontWeight: FontWeight.bold, fontSize: 13))]));

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(15)),
      title: Text('${widget.date.month}월 ${widget.date.day}일 농장 기록'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (widget.env != null) ...[
            _row('온도', '${widget.env!.minTemp}~${widget.env!.maxTemp}°C', Colors.red),
            _row('습도', '${widget.env!.minHumid}~${widget.env!.maxHumid}%', Colors.blue),
            const Divider(),
          ],
          if (_isEditing)
            TextField(controller: _controller, maxLength: 8, decoration: const InputDecoration(hintText: '메모 (최대 8자)', counterText: ""), autofocus: true)
          else
            Container(
              width: double.infinity, padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(color: Colors.grey.shade100, borderRadius: BorderRadius.circular(8)),
              child: Text(_controller.text.isEmpty ? '등록된 메모가 없습니다.' : _controller.text, style: TextStyle(color: _controller.text.isEmpty ? Colors.grey : Colors.black87)),
            ),
        ],
      ),
      actions: _isEditing
          ? [
        TextButton(onPressed: () => setState(() { _controller.text = widget.provider.getNoteForDate(widget.ymd); _isEditing = false; }), child: const Text('취소')),
        ElevatedButton(onPressed: () { widget.provider.saveNoteForDate(widget.ymd, _controller.text); Navigator.pop(context); }, child: const Text('저장')),
      ]
          : [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('닫기')),
        ElevatedButton(onPressed: () => setState(() => _isEditing = true), child: const Text('메모 수정')),
      ],
    );
  }
}
