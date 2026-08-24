// lib/screens/screen_crop_edit.dart
import 'package:flutter/material.dart';
import '../core/app_theme.dart';
import '../widgets/app_widgets.dart';
import '../services/service_crop_data.dart';
import '../models/app_models.dart';

class CropEditScreen extends StatefulWidget {
  final List<CropModel> currentFruits;
  const CropEditScreen({super.key, required this.currentFruits});
  @override
  State<CropEditScreen> createState() => _CropEditScreenState();
}

class _CropEditScreenState extends State<CropEditScreen> {
  late List<CropModel> _editableFruits;

  @override
  void initState() {
    super.initState();
    _editableFruits = widget.currentFruits.map((fruit) =>
        CropModel(cropId: fruit.cropId, name: fruit.name, icon: fruit.icon)
    ).toList();
  }

  void _editFruitDialog(int index) {
    final nameController = TextEditingController(text: _editableFruits[index].name);
    final iconController = TextEditingController(text: _editableFruits[index].icon);

    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('작물 편집'),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(controller: iconController, decoration: const InputDecoration(labelText: '이모지 (아이콘)', hintText: '예: 🍉')),
              const SizedBox(height: 16),
              TextField(controller: nameController, decoration: const InputDecoration(labelText: '작물 이름', hintText: '빈칸으로 두면 작물이 삭제됩니다.')),
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context), child: const Text('취소', style: TextStyle(color: Colors.grey))),
            ElevatedButton(
              onPressed: () {
                setState(() {
                  _editableFruits[index].name = nameController.text.trim();
                  _editableFruits[index].icon = iconController.text.trim();
                });
                Navigator.pop(context);
              },
              style: ElevatedButton.styleFrom(backgroundColor: AppColors.primary, foregroundColor: Colors.white),
              child: const Text('저장'),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return EcoGlassScaffold(
      title: const Text('작물 등록'),
      builder: (context, topPadding, bottomPadding) {
        return Padding(
          padding: EdgeInsets.only(top: topPadding, left: 16, right: 16, bottom: bottomPadding),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('대시보드 작물 리스트 설정', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.primary)),
              const SizedBox(height: 8),
              const Text('이름을 빈칸으로 저장하면 해당 작물이 비활성화됩니다.', style: TextStyle(color: Colors.grey)),
              const SizedBox(height: 16),
              Expanded(
                child: ListView.builder(
                  padding: EdgeInsets.zero,
                  itemCount: _editableFruits.length,
                  itemBuilder: (context, index) {
                    final fruit = _editableFruits[index];
                    final isEmpty = fruit.name.trim().isEmpty;

                    return Card(
                      elevation: 0, margin: const EdgeInsets.only(bottom: 12),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12), side: BorderSide(color: isEmpty ? Colors.grey.shade300 : Colors.grey.shade200)),
                      child: ListTile(
                        // 🌟 이름/아이콘이 비워졌을 때 표시할 문구 처리
                        leading: SizedBox(width: 50, child: FittedBox(fit: BoxFit.scaleDown, child: Text(fruit.icon.isEmpty ? '❔' : fruit.icon, style: const TextStyle(fontSize: 32)))),
                        title: FittedBox(fit: BoxFit.scaleDown, alignment: Alignment.centerLeft, child: Text(isEmpty ? '(비어있음)' : fruit.name, style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18, color: isEmpty ? Colors.grey : Colors.black))),
                        // 🌟 작물 ID 노출되던 서브타이틀 완전 삭제
                        trailing: Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(color: AppColors.primary.withValues(alpha: 0.1), shape: BoxShape.circle),
                          child: const Icon(Icons.edit_rounded, color: AppColors.primary, size: 20),
                        ),
                        onTap: () => _editFruitDialog(index),
                      ),
                    );
                  },
                ),
              ),
              const SizedBox(height: 16),
              PrimaryButton(
                text: '변경 사항 적용 및 영구 저장',
                onPressed: () async {
                  await CropDataService.saveLocalCropMetadata(_editableFruits);
                  if (!context.mounted) return;
                  ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('✅ 설정이 기기에 저장되었습니다.')));
                  Navigator.pop(context, _editableFruits);
                },
              ),
            ],
          ),
        );
      },
    );
  }
}
