package com.omni.smart.mqtt;

import android.content.Context;
import android.util.Log;

import org.eclipse.paho.client.mqttv3.IMqttActionListener;
import org.eclipse.paho.client.mqttv3.IMqttToken;
import org.eclipse.paho.client.mqttv3.MqttAsyncClient;
import org.eclipse.paho.client.mqttv3.MqttConnectOptions;
import org.eclipse.paho.client.mqttv3.MqttException;
import org.eclipse.paho.client.mqttv3.MqttMessage;
import org.eclipse.paho.client.mqttv3.TimerPingSender;
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence;

public class MqttHelper {
    private static final String TAG = "MqttHelper";
    private static final String SERVER_URI = "tcp://192.168.137.36:1883";
    private static final String CLIENT_ID = "HangFitAndroidClient";
    private static final String TOPIC = "rail/target_qr";

    private MqttAsyncClient mqttClient;

    public MqttHelper(Context context) {
        try {
            mqttClient = new MqttAsyncClient(SERVER_URI, CLIENT_ID, new MemoryPersistence(), new TimerPingSender());
        } catch (MqttException e) {
            Log.e(TAG, "Initialization failed: " + e.getMessage());
        }
    }

    public void connect(IMqttActionListener callback) {
        if (mqttClient == null) return;

        MqttConnectOptions options = new MqttConnectOptions();
        options.setAutomaticReconnect(true);
        options.setCleanSession(true);
        options.setConnectionTimeout(30);
        options.setKeepAliveInterval(60);

        try {
            mqttClient.connect(options, null, callback);
        } catch (MqttException e) {
            Log.e(TAG, "Connect failed: " + e.getMessage());
        }
    }

    // 기존 publish는 그대로 유지 (다른 곳에서 쓰고 있을 수 있으니)
    public void publish(String message) {
        publish(message, null);
    }

    // 새로 추가: 결과 콜백을 받는 publish
    public void publish(String message, IMqttActionListener callback) {
        if (mqttClient == null || !mqttClient.isConnected()) {
            Log.e(TAG, "Cannot publish: client not connected");
            if (callback != null) {
                callback.onFailure(null, new MqttException(MqttException.REASON_CODE_CLIENT_NOT_CONNECTED));
            }
            return;
        }

        try {
            MqttMessage mqttMessage = new MqttMessage();
            mqttMessage.setPayload(message.getBytes());
            mqttClient.publish(TOPIC, mqttMessage, null, callback);
            Log.d(TAG, "Message published to " + TOPIC + ": " + message);
        } catch (MqttException e) {
            Log.e(TAG, "Publish failed: " + e.getMessage());
            if (callback != null) {
                callback.onFailure(null, e);
            }
        }
    }

    public void disconnect() {
        try {
            if (mqttClient != null && mqttClient.isConnected()) {
                mqttClient.disconnect();
            }
        } catch (MqttException e) {
            Log.e(TAG, "Disconnect failed: " + e.getMessage());
        }
    }

    public boolean isConnected() {
        return mqttClient != null && mqttClient.isConnected();
    }
}