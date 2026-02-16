import 'package:flutter/material.dart';
import 'package:flutter_mp_pose_landmarker/flutter_mp_pose_landmarker.dart';
import '../utils/math_utils.dart';
import '../models/difficulty_config.dart';

class CardioExerciseLogic {
  int consecutiveCorrect = 0;
  bool stageIncremented = false;
  int growthCooldown = 0;

  /// Process a pose frame. Returns true if a point was scored.
  bool process(List<PoseLandmarkPoint> l, DifficultyConfig config) {
    // MediaPipe landmark indices:
    // 11=left_shoulder, 12=right_shoulder
    // 15=left_wrist, 16=right_wrist
    // 23=left_hip, 24=right_hip
    // 27=left_ankle, 28=right_ankle

    final shoulderL = Offset(l[11].x, l[11].y);
    final wristL = Offset(l[15].x, l[15].y);
    final hipL = Offset(l[23].x, l[23].y);

    final shoulderR = Offset(l[12].x, l[12].y);
    final wristR = Offset(l[16].x, l[16].y);
    final hipR = Offset(l[24].x, l[24].y);

    final ankleL = Offset(l[27].x, l[27].y);
    final ankleR = Offset(l[28].x, l[28].y);

    // Left arm: compute unsigned angle, then sign it
    final torsoVecL = hipL - shoulderL;
    final armVecL = wristL - shoulderL;
    double angleL = angleBetween(torsoVecL, armVecL);
    // Positive if wrist is to the left of shoulder (open), negative if crossed
    angleL = (wristL.dx > shoulderL.dx) ? angleL : -angleL;
    angleL = angleL.clamp(-90, 90);
    final leftArmCrossed = angleL < 0;

    // Right arm: compute unsigned angle, then sign it (mirrored)
    final torsoVecR = hipR - shoulderR;
    final armVecR = wristR - shoulderR;
    double angleR = angleBetween(torsoVecR, armVecR);
    // Positive if wrist is to the right of shoulder (open), negative if crossed
    angleR = (wristR.dx < shoulderR.dx) ? angleR : -angleR;
    angleR = angleR.clamp(-90, 90);
    final rightArmCrossed = angleR < 0;

    // Legs: closed when ankles are close together
    final ankleDist = (ankleR - ankleL).distance;
    final legsClosed = ankleDist <= 0.25;

    final poseCorrect = leftArmCrossed && rightArmCrossed && legsClosed;

    // Handle cooldown after scoring
    if (growthCooldown > 0) {
      growthCooldown--;
      if (growthCooldown == 0) {
        stageIncremented = false;
      }
      return false;
    }

    if (poseCorrect) {
      consecutiveCorrect++;
      if (consecutiveCorrect >= config.growthThreshold && !stageIncremented) {
        growthCooldown = config.cooldownFrames;
        stageIncremented = true;
        consecutiveCorrect = 0;
        return true; // scored!
      }
    } else {
      consecutiveCorrect = 0;
      stageIncremented = false;
    }

    return false;
  }

  void reset() {
    consecutiveCorrect = 0;
    stageIncremented = false;
    growthCooldown = 0;
  }
}
