package com.omni.smart.activity;

import com.omni.smart.R;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import com.omni.smart.activity.MainActivity;

public class LoginActivity extends AppCompatActivity {

    private SharedPreferences prefs;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_login);

        prefs = getSharedPreferences("user_auth", MODE_PRIVATE);

        if (prefs.getBoolean("is_logged_in", false)) {
            goToMain();
            return;
        }

        EditText etId = findViewById(R.id.etId);
        EditText etPw = findViewById(R.id.etPw);
        Button btnLogin = findViewById(R.id.btnLogin);
        TextView tvSignup = findViewById(R.id.tvSignup);

        btnLogin.setOnClickListener(v -> {
            String id = etId.getText().toString().trim();
            String pw = etPw.getText().toString().trim();

            if (id.isEmpty() || pw.isEmpty()) {
                Toast.makeText(this, "아이디/비번 입력해줘", Toast.LENGTH_SHORT).show();
                return;
            }

            String savedId = prefs.getString("saved_id", null);
            String savedPw = prefs.getString("saved_pw", null);

            if (savedId == null) {
                Toast.makeText(this, "가입된 계정이 없어. 회원가입 먼저 해줘", Toast.LENGTH_SHORT).show();
            } else if (id.equals(savedId) && pw.equals(savedPw)) {
                prefs.edit().putBoolean("is_logged_in", true).apply();
                goToMain();
            } else {
                Toast.makeText(this, "아이디 또는 비밀번호가 틀렸어", Toast.LENGTH_SHORT).show();
            }
        });

        tvSignup.setOnClickListener(v ->
                startActivity(new Intent(this, SignupActivity.class)));
    }

    private void goToMain() {
        startActivity(new Intent(this, MainActivity.class));
        finish();
    }
}