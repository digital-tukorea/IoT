import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'providers/auth_provider.dart';
import 'providers/robot_provider.dart';
import 'providers/environment_provider.dart';
import 'providers/crop_provider.dart';
import 'providers/alert_provider.dart';
import 'screens/screen_login.dart';
import 'core/app_theme.dart';

// [앱 시작점] 앱의 최상위 위젯. 공통 테마를 주입하고 첫 화면을 지정합니다.
void main() {
  runApp(
      MultiProvider(
        providers: [
          ChangeNotifierProvider(create: (_) => AuthProvider()),
          ChangeNotifierProvider(create: (_) => RobotProvider()),
          ChangeNotifierProvider(create: (_) => EnvironmentProvider()),
          ChangeNotifierProvider(create: (_) => CropProvider()),
          ChangeNotifierProvider(create: (_) => AlertProvider()),
        ],
        child:const MyApp(),
      ),
  );
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'kdt1조 스마트팜(딸기딸기)',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.themeData,
      home: const LoginScreen(),
    );
  }
}