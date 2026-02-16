import 'package:flutter/material.dart';
import 'package:flutter_mp_pose_landmarker/flutter_mp_pose_landmarker.dart';

class PosePainter extends CustomPainter {
  final List<PoseLandmarkPoint> landmarks;

  PosePainter(this.landmarks);

  @override
  void paint(Canvas canvas, Size size) {
    final linePaint = Paint()
      ..color = Colors.greenAccent
      ..strokeWidth = 3
      ..style = PaintingStyle.stroke;

    final jointPaint = Paint()
      ..color = Colors.green
      ..style = PaintingStyle.fill;

    // Draw skeleton connections
    _drawSkeleton(canvas, size, linePaint);

    // Draw joints on top
    for (final lm in landmarks) {
      canvas.drawCircle(
        Offset(lm.x * size.width, lm.y * size.height),
        5,
        jointPaint,
      );
    }
  }

  void _drawSkeleton(Canvas canvas, Size size, Paint paint) {
    // Helper function to draw line between two landmarks
    void drawLine(int startIdx, int endIdx) {
      if (startIdx >= landmarks.length || endIdx >= landmarks.length) return;

      final start = landmarks[startIdx];
      final end = landmarks[endIdx];

      canvas.drawLine(
        Offset(start.x * size.width, start.y * size.height),
        Offset(end.x * size.width, end.y * size.height),
        paint,
      );
    }

    // Face connections
    drawLine(0, 1);   // Nose to left eye inner
    drawLine(1, 2);   // Left eye inner to left eye
    drawLine(2, 3);   // Left eye to left eye outer
    drawLine(0, 4);   // Nose to right eye inner
    drawLine(4, 5);   // Right eye inner to right eye
    drawLine(5, 6);   // Right eye to right eye outer
    drawLine(0, 7);   // Nose to left ear
    drawLine(0, 8);   // Nose to right ear

    // Torso connections
    drawLine(11, 12); // Left shoulder to right shoulder
    drawLine(11, 23); // Left shoulder to left hip
    drawLine(12, 24); // Right shoulder to right hip
    drawLine(23, 24); // Left hip to right hip

    // Left arm
    drawLine(11, 13); // Left shoulder to left elbow
    drawLine(13, 15); // Left elbow to left wrist
    drawLine(15, 17); // Left wrist to left pinky
    drawLine(15, 19); // Left wrist to left index
    drawLine(15, 21); // Left wrist to left thumb
    drawLine(17, 19); // Left pinky to left index

    // Right arm
    drawLine(12, 14); // Right shoulder to right elbow
    drawLine(14, 16); // Right elbow to right wrist
    drawLine(16, 18); // Right wrist to right pinky
    drawLine(16, 20); // Right wrist to right index
    drawLine(16, 22); // Right wrist to right thumb
    drawLine(18, 20); // Right pinky to right index

    // Left leg
    drawLine(23, 25); // Left hip to left knee
    drawLine(25, 27); // Left knee to left ankle
    drawLine(27, 29); // Left ankle to left heel
    drawLine(27, 31); // Left ankle to left foot index

    // Right leg
    drawLine(24, 26); // Right hip to right knee
    drawLine(26, 28); // Right knee to right ankle
    drawLine(28, 30); // Right ankle to right heel
    drawLine(28, 32); // Right ankle to right foot index
  }

  @override
  bool shouldRepaint(covariant PosePainter oldDelegate) => true;
}
