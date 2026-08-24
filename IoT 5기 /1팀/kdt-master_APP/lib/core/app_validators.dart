

class AppValidators {
  // 1. 아이디 검사 (필수 + 4자 이상)
  static String? validateId(String? value) {
    if (value == null || value.trim().isEmpty) {
      return '아이디를 입력해주세요.';
    }
    if (value.trim().length < 4) {
      return '아이디는 4자 이상이어야 합니다.';
    }
    return null;
  }

  // 2. 비밀번호 검사 (필수 + 6자 이상)
  static String? validatePassword(String? value) {
    if (value == null || value.trim().isEmpty) {
      return '비밀번호를 입력해주세요.';
    }
    if (value.trim().length < 6) {
      return '비밀번호는 6자 이상이어야 합니다.';
    }
    return null;
  }

  // 3. 이름 검사 (필수 + 2자 이상)
  static String? validateName(String? value) {
    if (value == null || value.trim().isEmpty) {
      return '이름을 입력해주세요.';
    }
    if (value.trim().length < 2) {
      return '이름은 2자 이상 입력해주세요.';
    }
    return null;
  }

  // 4. 전화번호 검사 (필수 + 정규식)
  static String? validatePhone(String? value) {
    if (value == null || value.trim().isEmpty) {
      return '전화번호를 입력해주세요.';
    }
    final phoneRegExp = RegExp(r'^\d{2,3}-?\d{3,4}-?\d{4}$');
    if (!phoneRegExp.hasMatch(value.trim())) {
      return '올바른 전화번호 형식이 아닙니다.';
    }
    return null;
  }

  // 5. 이메일 검사 (필수 + 정규식)
  static String? validateEmail(String? value) {
    if (value == null || value.trim().isEmpty) {
      return '이메일을 입력해주세요.';
    }
    final emailRegExp = RegExp(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$');
    if (!emailRegExp.hasMatch(value.trim())) {
      return '올바른 이메일 형식이 아닙니다. (예: user@example.com)';
    }
    return null;
  }

  // 6. 국가 검사 (선택 항목 + 입력 시 정규식)
  static String? validateCountry(String? value) {
    if (value == null || value.trim().isEmpty) {
      return null; // 선택 항목이므로 비어있으면 통과
    }
    final countryRegExp = RegExp(r'^[a-zA-Z]{2,3}$');
    if (!countryRegExp.hasMatch(value.trim())) {
      return '국가 코드는 2~3자리 영문입니다. (예: KR, US)';
    }
    return null;
  }
}