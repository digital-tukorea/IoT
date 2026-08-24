// lib/services/service_mqtt.dart
import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:mqtt_client/mqtt_client.dart';
import 'package:mqtt_client/mqtt_server_client.dart';
import '../core/api_config.dart';

class MqttService {
  static final MqttService _instance = MqttService._internal();
  factory MqttService() => _instance;
  MqttService._internal();

  MqttServerClient? _client;
  bool _isConnected = false;
  String? _currentUserId;

  final _messageController = StreamController<Map<String, dynamic>>.broadcast();
  Stream<Map<String, dynamic>> get messageStream => _messageController.stream;

  bool get isConnected => _isConnected;

  Future<void> connect(String userId) async {
    if (_isConnected && _currentUserId != userId) {
      disconnect();
    }
    if (_isConnected) return;

    _currentUserId = userId;
    final String clientId = 'flutter_global_${userId}_${DateTime.now().millisecondsSinceEpoch}';
    _client = MqttServerClient(ApiConfig.serverIp, clientId);
    _client!.port = ApiConfig.mqttPort;
    _client!.keepAlivePeriod = 20;
    _client!.logging(on: false);

    _client!.onDisconnected = () {
      _isConnected = false;
      if (_currentUserId == userId) {
        Future.delayed(const Duration(seconds: 5), () {
          if (_currentUserId == userId) connect(userId);
        });
      }
    };

    final connMess = MqttConnectMessage().withClientIdentifier(clientId).startClean();
    _client!.connectionMessage = connMess;

    try {
      await _client!.connect();
      _isConnected = true;
      _client!.subscribe('ddalgi/robot/status', MqttQos.atMostOnce);
      _client!.subscribe(ApiConfig.diseaseAlertTopic(userId), MqttQos.atMostOnce);

      _client!.updates!.listen((List<MqttReceivedMessage<MqttMessage>> c) {
        final MqttPublishMessage recMess = c[0].payload as MqttPublishMessage;
        final String pt = MqttPublishPayload.bytesToStringAsString(recMess.payload.message);

        // 🌟 Type Casting 크래시 방지 및 안전한 파싱
        try {
          if (pt.isNotEmpty) {
            final dynamic decoded = jsonDecode(pt);
            if (decoded is Map<String, dynamic>) {
              decoded['topic'] = c[0].topic;
              _messageController.add(decoded);
            }
          }
        } catch (e) {
          debugPrint('❌ MQTT 데이터 파싱 에러: $e');
        }
      });
    } catch (e) {
      _client?.disconnect();
      _isConnected = false;
      _currentUserId = null;
    }
  }

  void disconnect() {
    _client?.disconnect();
    _isConnected = false;
    _currentUserId = null;
  }
}
