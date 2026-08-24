package com.omni.smart.util;

import android.content.Context;
import android.location.Address;
import android.location.Geocoder;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;

import java.util.List;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * 위도/경도 -> "시흥시 정왕동" 형태의 한국어 동 단위 주소로 변환.
 * Geocoder.getFromLocation()은 동기(blocking) + 네트워크 호출이라 반드시
 * 백그라운드 스레드에서 실행해야 함 (메인 스레드에서 돌리면 ANR/느림).
 */
public class GeocodingHelper {
    private static final String TAG = "GeocodingHelper";
    private static final ExecutorService executor = Executors.newSingleThreadExecutor();
    private static final Handler mainHandler = new Handler(Looper.getMainLooper());

    public interface OnAddressResult {
        void onResult(String address);
    }

    public static void getAddressFromLocation(Context context, double lat, double lon, OnAddressResult callback) {
        executor.execute(() -> {
            String result = null;
            try {
                Geocoder geocoder = new Geocoder(context, Locale.KOREA);
                List<Address> addresses = geocoder.getFromLocation(lat, lon, 1);
                if (addresses != null && !addresses.isEmpty()) {
                    Address addr = addresses.get(0);
                    // 시/군/구
                    String city = addr.getLocality();
                    if (city == null) city = addr.getSubAdminArea();
                    // 동/읍/면
                    String dong = addr.getSubLocality();
                    if (dong == null) dong = addr.getThoroughfare();

                    if (city != null && dong != null) {
                        result = city + " " + dong;
                    } else if (city != null) {
                        result = city;
                    } else if (addr.getAddressLine(0) != null) {
                        result = addr.getAddressLine(0);
                    }
                }
            } catch (Exception e) {
                Log.e(TAG, "Geocoding failed: " + e.getMessage());
            }

            final String finalResult = (result != null) ? result : "위치 정보 없음";
            mainHandler.post(() -> callback.onResult(finalResult));
        });
    }
}