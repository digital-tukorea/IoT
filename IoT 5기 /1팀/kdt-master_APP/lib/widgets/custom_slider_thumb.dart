// lib/custom_slider_thumb.dart
import 'package:flutter/material.dart';
import 'dart:math' as math;
import '../core/app_theme.dart';

class StreamFlowTrackShape extends SliderTrackShape with BaseSliderTrackShape {
  final Animation<double> waveAnimation;

  StreamFlowTrackShape({required this.waveAnimation});

  @override
  void paint(
      PaintingContext context,
      Offset offset, {
        required RenderBox parentBox,
        required SliderThemeData sliderTheme,
        required Animation<double> enableAnimation,
        required TextDirection textDirection,
        required Offset thumbCenter,
        Offset? secondaryOffset,
        bool isDiscrete = false,
        bool isEnabled = false,
        double additionalActiveTrackHeight = 2,
      }) {
    final Canvas canvas = context.canvas;

    final Rect trackRect = getPreferredRect(
      parentBox: parentBox, offset: offset, sliderTheme: sliderTheme, isEnabled: isEnabled, isDiscrete: isDiscrete,
    );

    final RRect trackRRect = RRect.fromRectAndRadius(trackRect, Radius.circular(trackRect.height / 2));

    final Paint inactivePaint = Paint()..color = AppColors.primary.withValues(alpha: 0.1);
    canvas.drawRRect(trackRRect, inactivePaint);

    final Rect activeRect = Rect.fromLTRB(trackRect.left, trackRect.top, thumbCenter.dx, trackRect.bottom);

    canvas.save();
    canvas.clipRRect(trackRRect);

    final Paint activeBasePaint = Paint()..color = AppColors.primary.withValues(alpha: 0.3);
    canvas.drawRect(activeRect, activeBasePaint);

    final double amplitude = trackRect.height / 4;
    final double frequency = 30.0;
    final double phaseShift = waveAnimation.value * 2 * math.pi;

    final Paint wavePaint = Paint()
      ..color = Colors.white.withValues(alpha: 0.4)
      ..style = PaintingStyle.fill;

    Path wavePath = Path();
    wavePath.moveTo(activeRect.left, activeRect.bottom);

    for (double i = 0; i <= activeRect.width; i++) {
      double x = activeRect.left + i;
      double y = trackRect.center.dy + math.sin((i / frequency) + phaseShift) * amplitude;
      wavePath.lineTo(x, y);
    }

    wavePath.lineTo(activeRect.right, activeRect.bottom);
    wavePath.close();

    canvas.drawPath(wavePath, wavePaint);
    canvas.restore();
  }
}

class StreamPebbleThumbShape extends SliderComponentShape {
  final double value;
  final double thumbRadius;

  const StreamPebbleThumbShape({
    required this.value,
    this.thumbRadius = 22.0,
  });

  @override
  Size getPreferredSize(bool isEnabled, bool isDiscrete) {
    return Size.fromRadius(thumbRadius);
  }

  @override
  void paint(
      PaintingContext context, Offset center, {
        required Animation<double> activationAnimation, required Animation<double> enableAnimation,
        required bool isDiscrete, required TextPainter labelPainter, required RenderBox parentBox,
        required SliderThemeData sliderTheme, required TextDirection textDirection,
        required double value, required double textScaleFactor, required Size sizeWithOverflow,
      }) {
    final Canvas canvas = context.canvas;

    final Rect thumbRect = Rect.fromCenter(
      center: center,
      width: thumbRadius * 3.6,
      height: thumbRadius * 2.7,
    );
    final Path thumbPath = Path()..addOval(thumbRect);

    canvas.drawShadow(thumbPath, Colors.black.withValues(alpha: 0.2), 6.0, true);

    final Paint fillPaint = Paint()..color = AppColors.sliderThumb..style = PaintingStyle.fill;
    canvas.drawPath(thumbPath, fillPaint);

    // 🌟 수정 1: 슬라이더 값(0.0~1.0)에 따라 '동작' 또는 '정지' 텍스트 결정
    final bool isActive = value >= 0.5;
    final String labelText = isActive ? '동작' : '정지';

    final Offset labelCenter = Offset(center.dx, center.dy - thumbRadius - 32);

    // 🌟 수정 2: '동작'일 때는 녹색, '정지'일 때는 회색으로 말풍선 색상 동적 변경
    final Paint labelBgPaint = Paint()
      ..color = isActive ? AppColors.primary : Colors.grey.shade600
      ..style = PaintingStyle.fill;

    // 한글 두 글자가 넉넉히 들어가도록 가로폭 46.0으로 여유 부여
    final Rect labelRect = Rect.fromCenter(center: labelCenter, width: 46.0, height: 26.0);
    final RRect roundedLabelRect = RRect.fromRectAndRadius(labelRect, const Radius.circular(13));

    canvas.drawShadow(Path()..addRRect(roundedLabelRect), Colors.black.withValues(alpha: 0.15), 3.0, true);
    canvas.drawRRect(roundedLabelRect, labelBgPaint);

    final TextSpan span = TextSpan(
      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white),
      text: labelText,
    );

    final TextPainter tp = TextPainter(text: span, textAlign: TextAlign.center, textDirection: TextDirection.ltr);
    tp.layout();

    final Offset textOffset = Offset(
      labelCenter.dx - (tp.width / 2),
      labelCenter.dy - (tp.height / 2),
    );
    tp.paint(canvas, textOffset);
  }
}
