package com.omni.smart.activity;

import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;

import com.omni.smart.helper.PermissionHelper;
import com.omni.smart.util.EdgeToEdgeHelper;

public class SplashActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        EdgeToEdgeHelper.enable(getWindow());
        super.onCreate(savedInstanceState);
        setContentView(com.omni.smart.R.layout.activity_splash);

        checkPermissions();
    }

    private void checkPermissions() {
        if (PermissionHelper.hasPermissions(this)) {
            startMainActivity();
        } else {
            PermissionHelper.requestPermissions(this);
        }
    }

    private void startMainActivity() {
        new Handler(Looper.getMainLooper()).postDelayed(() -> {
            android.content.SharedPreferences prefs = getSharedPreferences("user_auth", MODE_PRIVATE);
            boolean isLoggedIn = prefs.getBoolean("is_logged_in", false);

            Class<?> nextActivity = isLoggedIn ? MainActivity.class : LoginActivity.class;

            startActivity(new Intent(SplashActivity.this, nextActivity));
            finish();
        }, 1500);
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions, @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == PermissionHelper.PERMISSION_REQUEST_CODE) {
            if (PermissionHelper.hasPermissions(this)) {
                startMainActivity();
            } else {
                // In a real app, show a dialog explaining why permissions are needed
                // For now, just request again or exit
                PermissionHelper.requestPermissions(this);
            }
        }
    }
}
