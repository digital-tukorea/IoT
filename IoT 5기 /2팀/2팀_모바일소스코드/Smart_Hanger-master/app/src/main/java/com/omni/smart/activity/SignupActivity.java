package com.omni.smart.activity;

import com.omni.smart.R;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.widget.Button;
import android.widget.EditText;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;

public class SignupActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_signup);

        SharedPreferences prefs = getSharedPreferences("user_auth", MODE_PRIVATE);
        EditText etId = findViewById(R.id.etId2);
        EditText etPw = findViewById(R.id.etPw2);
        Button btnSignup = findViewById(R.id.btnSignup);

        btnSignup.setOnClickListener(v -> {
            String id = etId.getText().toString().trim();
            String pw = etPw.getText().toString().trim();

            if (id.isEmpty() || pw.isEmpty()) {
                Toast.makeText(this, "아이디/비번 입력해줘", Toast.LENGTH_SHORT).show();
                return;
            }

            prefs.edit()
                    .putString("saved_id", id)
                    .putString("saved_pw", pw)
                    .apply();

            Toast.makeText(this, "가입 완료. 로그인해줘", Toast.LENGTH_SHORT).show();
            finish();
        });
    }
}