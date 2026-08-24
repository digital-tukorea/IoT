import 'package:flutter/material.dart';
import '../../core/app_theme.dart';

class CustomTextButton extends StatelessWidget {
  final String text;
  final VoidCallback onPressed;

  const CustomTextButton({
    super.key,
    required this.text,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return TextButton(
      style: TextButton.styleFrom(
        foregroundColor: AppColors.linkText,
      ),
      onPressed: onPressed,
      child: Text(text),
    );
  }
}
