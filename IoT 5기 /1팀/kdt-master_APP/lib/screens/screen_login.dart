// lib/screens/screen_login.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'screen_signup.dart';
import 'screen_selection.dart';
import '../widgets/app_widgets.dart'; // EcoGlassScaffold 포함
import '../services/service_auth.dart';
import '../models/app_models.dart';
import '../providers/auth_provider.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final TextEditingController _idController = TextEditingController();
  final TextEditingController _pwController = TextEditingController();
  final AuthService _authService = AuthService();
  bool isLoading = false;

  @override
  void dispose() {
    _idController.dispose();
    _pwController.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    final userId = _idController.text.trim();
    final password = _pwController.text.trim();

    if (userId.isEmpty || password.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('아이디와 비밀번호를 입력해주세요.')));
      return;
    }
    setState(() => isLoading = true);

    final result = await _authService.login(userId: userId, password: password);
    if (!mounted) return;
    setState(() => isLoading = false);

    if (result['success']) {
      final user = UserModel.fromJson(result['data']);
      context.read<AuthProvider>().setUser(user);

      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('✅ ${result['message']}')));
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (context) => const FruitSelectionScreen()),
      );
    } else {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('❌ ${result['message']}')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return EcoGlassScaffold(
      title: const Text('🍓 Ddalgi Farm 로그인'),
      builder: (context, topPadding, bottomPadding) {
        return LayoutBuilder(
          builder: (context, constraints) {
            return SingleChildScrollView(
              padding: EdgeInsets.only(
                top: topPadding,
                left: 24, right: 24,
                bottom: bottomPadding + 8.0, // 키보드 회피를 위해 살짝 더 줌
              ),
              child: ConstrainedBox(
                constraints: BoxConstraints(
                  // 🌟 화면 중앙 정렬을 위한 최소 높이 계산 (넘겨받은 패딩 활용)
                  minHeight: constraints.maxHeight - (topPadding + bottomPadding + 8.0),
                ),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    CustomTextField(controller: _idController, labelText: 'ID'),
                    const SizedBox(height: 16),
                    CustomTextField(controller: _pwController, labelText: 'PW', isPassword: true),
                    const SizedBox(height: 24),
                    PrimaryButton(text: '로그인', isLoading: isLoading, onPressed: _login),
                    const SizedBox(height: 12),
                    CustomTextButton(
                      text: '계정이 없으신가요? 회원가입',
                      onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (context) => const SignupScreen())),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }
}