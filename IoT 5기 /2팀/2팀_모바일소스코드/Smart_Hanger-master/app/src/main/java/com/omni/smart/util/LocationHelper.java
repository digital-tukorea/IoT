package com.omni.smart.util;

import android.content.Context;
import android.location.Location;

import com.google.android.gms.tasks.OnSuccessListener;

public class LocationHelper {

    private static final double FIXED_LAT = 37.3434;
    private static final double FIXED_LON = 126.7369;
    // ================================================

    public LocationHelper(Context context) {
        // 실제 GPS/FusedLocationProviderClient는 시연 동안 사용하지 않음
    }

    public void getLastLocation(OnSuccessListener<Location> listener) {
        Location fixedLocation = new Location("fixed_demo_location");
        fixedLocation.setLatitude(FIXED_LAT);
        fixedLocation.setLongitude(FIXED_LON);
        listener.onSuccess(fixedLocation);
    }
}