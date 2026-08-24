// lib/controllers/controller_fruit_dashboard.dart
import 'package:flutter/material.dart';
import 'dart:math' as math;
import '../providers/crop_provider.dart';
import '../models/app_models.dart'; // 🌟 공유 모델 임포트

class FruitDashboardController extends ChangeNotifier {
  final String userId, fruitCode;
  final CropProvider cropProvider;
  
  List<RipenessData> ripenessList = [];
  int _selectedRange = 7;

  int get selectedRange => _selectedRange;

  FruitDashboardController({required this.userId, required this.fruitCode, required this.cropProvider}) {
    _initData();
  }

  void _initData() {
    final cached = cropProvider.getCachedRipeness(fruitCode);
    if (cached != null) {
      // 🌟 이제 캐시된 데이터와 타입이 일치하므로 안전하게 복사 가능
      ripenessList = List<RipenessData>.from(cached);
    } else {
      _generateDummyData();
    }
  }

  void setRange(int range) {
    _selectedRange = range;
    _generateDummyData();
    notifyListeners();
  }

  void _generateDummyData() {
    final random = math.Random();
    final now = DateTime.now();
    ripenessList = List.generate(_selectedRange, (index) {
      final dateStr = '${now.subtract(Duration(days: (_selectedRange - 1) - index)).month.toString().padLeft(2,'0')}/${now.subtract(Duration(days: (_selectedRange - 1) - index)).day.toString().padLeft(2,'0')}';
      return RipenessData(
        date: dateStr,
        unripeCount: 2 + random.nextInt(10), // 전역 로직과 동일하게 조정
        ripeCount: 40 + random.nextInt(40),
        overripeCount: random.nextInt(8),
      );
    });

    cropProvider.updateHarvestPrediction(fruitCode, ripenessList);
  }
}
