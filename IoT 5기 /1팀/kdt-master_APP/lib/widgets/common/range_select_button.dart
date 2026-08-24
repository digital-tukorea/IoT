// lib/widgets/common/range_select_button.dart
import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import '../../core/app_theme.dart';
import 'primary_button.dart';

class RangeSelectButton extends StatelessWidget {
  final String label;
  final int currentValue;
  final List<int> options;
  final Function(int) onSelected;

  const RangeSelectButton({
    super.key,
    required this.label,
    required this.currentValue,
    required this.options,
    required this.onSelected,
  });

  void _showPicker(BuildContext context) {
    // 🌟 Index -1 로 인한 바텀시트 크래시 방지
    int initialIndex = options.indexOf(currentValue);
    if (initialIndex < 0) initialIndex = 0;

    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (context) {
        return Container(
          height: 250,
          padding: const EdgeInsets.symmetric(vertical: 16),
          child: Column(
            children: [
              Text('$label 선택', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),
              Expanded(
                child: CupertinoPicker(
                  itemExtent: 40,
                  onSelectedItemChanged: (index) => onSelected(options[index]),
                  scrollController: FixedExtentScrollController(initialItem: initialIndex),
                  children: options.map((val) => Center(child: Text('$val $label'))).toList(),
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16.0),
                child: PrimaryButton(
                  text: '확인',
                  height: 44,
                  onPressed: () => Navigator.pop(context),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () => _showPicker(context),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: AppColors.primary.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.primary.withValues(alpha: 0.3)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('$currentValue$label', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppColors.primary)),
            const Icon(Icons.keyboard_arrow_down_rounded, size: 16, color: AppColors.primary),
          ],
        ),
      ),
    );
  }
}