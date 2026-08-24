import 'dart:ui';
import 'package:flutter/material.dart';
import '../../core/app_theme.dart';

class EcoGlassScaffold extends StatelessWidget {
  final Widget title;
  final Widget? leading;
  final List<Widget>? actions;
  final Widget Function(BuildContext context, double topPadding, double bottomPadding) builder;

  const EcoGlassScaffold({
    super.key,
    required this.title,
    required this.builder,
    this.leading,
    this.actions,
  });

  @override
  Widget build(BuildContext context) {
    final double topPadding = kToolbarHeight + MediaQuery.of(context).padding.top + 16.0;
    final double bottomPadding = MediaQuery.of(context).padding.bottom + 16.0;

    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: GlassAppBar(
        title: title,
        leading: leading,
        actions: actions,
      ),
      body: builder(context, topPadding, bottomPadding),
    );
  }
}

class GlassAppBar extends StatelessWidget implements PreferredSizeWidget {
  final Widget title;
  final List<Widget>? actions;
  final Widget? leading;

  const GlassAppBar({super.key, required this.title, this.actions, this.leading});

  @override
  Widget build(BuildContext context) {
    return ClipRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
        child: AppBar(
          title: title,
          actions: actions,
          leading: leading,
          backgroundColor: AppColors.primary.withValues(alpha: 0.85),
          elevation: 0,
        ),
      ),
    );
  }

  @override
  Size get preferredSize => const Size.fromHeight(kToolbarHeight);
}
