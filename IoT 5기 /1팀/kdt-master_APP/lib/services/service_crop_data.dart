// lib/services/service_crop_data.dart
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/app_models.dart';

class CropDataService {
  // 🌟 1. 기본 작물을 포도, 딸기, 참외 및 빈칸으로 변경
  static const Map<String, Map<String, String>> _defaultMetadata = {
    'grape': {'name': '포도', 'icon': '🍇'},
    'strawberry': {'name': '딸기', 'icon': '🍓'},
    'melon': {'name': '참외', 'icon': '🍈'},
    'empty_slot': {'name': '', 'icon': ''}, // 4번째는 비워둠
  };

  static Future<List<String>> _fetchCropIdsFromServer(String userId) async {
    await Future.delayed(const Duration(milliseconds: 500));
    return ['grape', 'strawberry', 'melon', 'empty_slot'];
  }

  static Future<List<CropModel>> getMergedCropData(String userId) async {
    final serverCropIds = await _fetchCropIdsFromServer(userId);
    final prefs = await SharedPreferences.getInstance();
    final localDataString = prefs.getString('local_crop_metadata');

    Map<String, dynamic> localMetadata = {};
    if (localDataString != null) {
      try {
        final decoded = jsonDecode(localDataString);
        if (decoded is Map<String, dynamic>) {
          localMetadata = decoded;
        }
      } catch (e) {
        debugPrint('로컬 작물 메타데이터 파싱 오류: $e');
      }
    }

    List<CropModel> mergedList = [];
    for (String cropId in serverCropIds) {
      // 🌟 로컬에 빈 문자열("")로 저장되었으면 ?? 연산자를 통과하여 그대로 빈 문자열이 유지됨
      String name = localMetadata[cropId]?['name'] ?? _defaultMetadata[cropId]?['name'] ?? '작물';
      String icon = localMetadata[cropId]?['icon'] ?? _defaultMetadata[cropId]?['icon'] ?? '🌱';
      mergedList.add(CropModel(cropId: cropId, name: name, icon: icon));
    }
    return mergedList;
  }

  static Future<void> saveLocalCropMetadata(List<CropModel> crops) async {
    final prefs = await SharedPreferences.getInstance();
    Map<String, dynamic> metadataToSave = {};
    for (var crop in crops) {
      metadataToSave[crop.cropId] = crop.toJson();
    }
    await prefs.setString('local_crop_metadata', jsonEncode(metadataToSave));
  }
}