import 'dart:async';
import 'package:flutter_mp_pose_landmarker/flutter_mp_pose_landmarker.dart';

class PoseService {
  List<PoseLandmarkPoint>? currentLandmarks;
  late StreamSubscription<PoseLandMarker> _poseSubscription;

  final Function(List<PoseLandmarkPoint>) onPoseDetected;

  PoseService({required this.onPoseDetected});

  Future<void> initialize() async {
    // Configure MediaPipe Pose (THIS IS THE ONLY WAY)
    PoseLandmarker.setConfig(
      delegate: 0, // 0 = CPU, 1 = GPU
      model: 1,    // 0 = Full, 1 = Lite, 2 = Heavy
      minPoseDetectionConfidence: 0.5,
      minPoseTrackingConfidence: 0.5,
      minPosePresenceConfidence: 0.5,
    );

    // Listen to pose landmark stream
    _poseSubscription =
        PoseLandmarker.poseLandmarkStream.listen((pose) {
      currentLandmarks = pose.landmarks;
      onPoseDetected(currentLandmarks!);
    });
  }

  void dispose() {
    _poseSubscription.cancel();
  }
}
