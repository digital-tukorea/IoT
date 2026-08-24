// lib/screens/screen_signup.dart
import 'package:flutter/material.dart';
import '../widgets/app_widgets.dart';
import '../core/app_validators.dart';
import '../services/service_auth.dart';

class SignupScreen extends StatefulWidget {
  const SignupScreen({super.key});

  @override
  State<SignupScreen> createState() => _SignupScreenState();
}

class _SignupScreenState extends State<SignupScreen> {
  final _formKey = GlobalKey<FormState>();
  final _idController = TextEditingController();
  final _pwController = TextEditingController();
  final _nameController = TextEditingController();
  final _phoneController = TextEditingController();
  final _emailController = TextEditingController();
  final _countryController = TextEditingController(text: 'KR');

  final AuthService _authService = AuthService();
  bool isLoading = false;

  @override
  void dispose() {
    _idController.dispose();
    _pwController.dispose();
    _nameController.dispose();
    _phoneController.dispose();
    _emailController.dispose();
    _countryController.dispose();
    super.dispose();
  }

  Future<void> _signup() async {
    if (!_formKey.currentState!.validate()) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('⚠️ 입력 양식을 다시 확인해 주세요.')));
      return;
    }
    setState(() => isLoading = true);

    final Map<String, dynamic> requestData = {
      'user_id': _idController.text.trim(),
      'password': _pwController.text.trim(),
      'name': _nameController.text.trim(),
      'phone_number': _phoneController.text.trim(),
      'email': _emailController.text.trim(),
      'country': _countryController.text.trim().isNotEmpty ? _countryController.text.trim() : 'KR',
    };

    final result = await _authService.signup(requestData);

    if (!mounted) return;
    setState(() => isLoading = false);

    if (result['success']) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('✅ ${result['message']}')));
      Navigator.pop(context);
    } else {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('❌ ${result['message']}')));
    }
  }

  @override
  Widget build(BuildContext context) {
    // 🌟 [모듈화 적용] 엄청나게 깔끔해진 뼈대
    return EcoGlassScaffold(
      title: const Text('🍓 Ddalgi Farm 회원가입'),
      builder: (context, topPadding, bottomPadding) {
        return SingleChildScrollView(
          // 🌟 모듈에서 넘겨준 자동 계산 패딩 사용
          padding: EdgeInsets.only(top: topPadding, left: 24, right: 24, bottom: bottomPadding),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Text('*표시 항목은 필수 입력 항목입니다.', style: TextStyle(color: Colors.red, fontSize: 12, fontWeight: FontWeight.bold), textAlign: TextAlign.center),
                const SizedBox(height: 16),
                CustomTextField(controller: _idController, labelText: '아이디 *', validator: AppValidators.validateId),
                const SizedBox(height: 12),
                CustomTextField(controller: _pwController, labelText: '비밀번호 *', isPassword: true, validator: AppValidators.validatePassword),
                const SizedBox(height: 12),
                CustomTextField(controller: _nameController, labelText: '이름 *', validator: AppValidators.validateName),
                const SizedBox(height: 12),
                CustomTextField(controller: _phoneController, labelText: '전화번호 *', keyboardType: TextInputType.phone, validator: AppValidators.validatePhone),
                const SizedBox(height: 12),
                CustomTextField(controller: _emailController, labelText: '이메일 *', keyboardType: TextInputType.emailAddress, validator: AppValidators.validateEmail),
                const SizedBox(height: 12),
                CustomTextField(controller: _countryController, labelText: '국가', validator: AppValidators.validateCountry),
                const SizedBox(height: 24),
                PrimaryButton(text: '가입하기', isLoading: isLoading, onPressed: _signup),
              ],
            ),
          ),
        );
      },
    );
  }
}