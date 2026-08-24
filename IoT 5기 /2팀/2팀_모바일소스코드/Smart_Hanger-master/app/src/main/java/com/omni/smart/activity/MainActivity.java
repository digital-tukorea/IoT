package com.omni.smart.activity;

import android.os.Bundle;
import androidx.appcompat.app.AppCompatActivity;
import androidx.fragment.app.Fragment;

import com.omni.smart.R;
import com.omni.smart.databinding.ActivityMainBinding;
import com.omni.smart.fragment.CalendarFragment;
import com.omni.smart.fragment.ClosetFragment;
import com.omni.smart.fragment.HomeFragment;
import com.omni.smart.fragment.RecommendFragment;
import com.omni.smart.util.EdgeToEdgeHelper;

public class MainActivity extends AppCompatActivity {
    private ActivityMainBinding binding;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        EdgeToEdgeHelper.enable(getWindow());
        // UI-only addition: EdgeToEdgeHelper always forces light (white) status bar icons,
        // which was correct for the old dark theme. Our new light/mint theme needs dark
        // icons instead, so we re-assert that here without touching EdgeToEdgeHelper.java.
        androidx.core.view.WindowCompat.getInsetsController(getWindow(), getWindow().getDecorView())
                .setAppearanceLightStatusBars(true);
        super.onCreate(savedInstanceState);
        binding = ActivityMainBinding.inflate(getLayoutInflater());
        setContentView(binding.getRoot());

        setupNavigation();

        if (!com.omni.smart.helper.PermissionHelper.hasPermissions(this)) {
            com.omni.smart.helper.PermissionHelper.requestPermissions(this);
        }

        if (savedInstanceState == null) {
            loadFragment(new HomeFragment());
        }

        if (getIntent().getBooleanExtra("OPEN_CALENDAR_TAB", false)) {
            binding.bottomNavigation.setSelectedItemId(R.id.nav_calendar);
        }

        com.omni.smart.receiver.LaundryAlarmReceiver.scheduleFirst(this);


    }

    private void setupNavigation() {
        binding.bottomNavigation.setOnItemSelectedListener(item -> {
            int itemId = item.getItemId();
            if (itemId == R.id.nav_home) {
                loadFragment(new HomeFragment());
                return true;
            } else if (itemId == R.id.nav_recommend) {
                loadFragment(new RecommendFragment());
                return true;
            } else if (itemId == R.id.nav_closet) {
                loadFragment(new ClosetFragment());
                return true;
            } else if (itemId == R.id.nav_calendar) {
                loadFragment(new CalendarFragment());
                return true;
            }
            return false;
        });
    }

    private void loadFragment(Fragment fragment) {
        getSupportFragmentManager().beginTransaction()
                .replace(R.id.fragment_container, fragment)
                .commit();
    }

    // UI-only addition: lets HomeFragment's "오늘 일정" row jump straight to the
    // 캘린더 tab without launching a new Activity instance.
    public void selectCalendarTab() {
        binding.bottomNavigation.setSelectedItemId(R.id.nav_calendar);
    }
}