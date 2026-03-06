package com.team1.countwaste;

import android.os.Bundle;
import androidx.appcompat.app.AppCompatActivity;
import androidx.fragment.app.Fragment;
import com.google.android.material.bottomnavigation.BottomNavigationView;

public class MainActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        BottomNavigationView navView = findViewById(R.id.bottom_navigation);

        // 네비게이션 아이템 선택 리스너 설정
        navView.setOnItemSelectedListener(item -> {
            Fragment selectedFragment = null;
            int itemId = item.getItemId();

            if (itemId == R.id.navigation_dashboard) {
                selectedFragment = new DashboardFragment();
            } else if (itemId == R.id.navigation_summary) {
                selectedFragment = new SummaryFragment();
            } else if (itemId == R.id.navigation_details) {
                selectedFragment = new DetailsFragment();
            }

            if (selectedFragment != null) {
                getSupportFragmentManager().beginTransaction()
                        .replace(R.id.nav_host_fragment, selectedFragment)
                        .commit();
            }
            return true;
        });

        // 앱 실행 시 첫 화면 설정 (Dashboard)
        if (savedInstanceState == null) {
            navView.setSelectedItemId(R.id.navigation_dashboard);
        }
    }

    // Mobius 통신 관련 DTO (기존 코드 호환 유지용)
    public static class CinCreateRequest {
        public Cin m2m_cin;
        public CinCreateRequest(String content) {
            this.m2m_cin = new Cin(content);
        }
        public static class Cin {
            public String con;
            public Cin(String con) {
                this.con = con;
            }
        }
    }
}
