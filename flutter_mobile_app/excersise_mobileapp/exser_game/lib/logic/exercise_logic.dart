import 'package:flutter/material.dart';
import 'package:flutter_mp_pose_landmarker/flutter_mp_pose_landmarker.dart';
import '../utils/math_utils.dart';

class ExerciseLogic {
  static int score = 0;
  static int stableFrames = 0;

  static void process(List<PoseLandmarkPoint> l) {
    final shoulderL = Offset(l[11].x, l[11].y);
    final wristL = Offset(l[15].x, l[15].y);
    final hipL = Offset(l[23].x, l[23].y);

    final shoulderR = Offset(l[12].x, l[12].y);
    final wristR = Offset(l[16].x, l[16].y);
    final hipR = Offset(l[24].x, l[24].y);

    final ankleL = Offset(l[27].x, l[27].y);
    final ankleR = Offset(l[28].x, l[28].y);

    final angleL = angleBetween(hipL - shoulderL, wristL - shoulderL);
    final angleR = angleBetween(hipR - shoulderR, wristR - shoulderR);

    final ankleDist = (ankleR - ankleL).distance;

    final armSwing = angleL > 30 && angleR > 30;
    final stepTouch = ankleDist > 0.25;

    if (armSwing && stepTouch) {
      stableFrames++;
      if (stableFrames > 12) {
        score++;
        stableFrames = 0;
      }
    } else {
      stableFrames = 0;
    }
  }
}
