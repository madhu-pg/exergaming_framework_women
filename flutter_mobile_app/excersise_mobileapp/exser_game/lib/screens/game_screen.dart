import 'package:exser_game/pose/native_camera_preview.dart';
import 'package:flutter/material.dart';
import 'package:flutter_mp_pose_landmarker/flutter_mp_pose_landmarker.dart';
import 'package:permission_handler/permission_handler.dart';
import '../pose/pose_service.dart';
import '../pose/pose_painter.dart';
import '../logic/exercise_logic.dart';

class GameScreen extends StatefulWidget {
  const GameScreen({super.key});

  @override
  State<GameScreen> createState() => _GameScreenState();
}

class _GameScreenState extends State<GameScreen> {
  PoseService? poseService;
  bool _isPermissionGranted = false;
  bool _isLoading = true;
  String _errorMessage = '';
  int _cameraFacing = 1; // 0 = back camera, 1 = front camera

  @override
  void initState() {
    super.initState();
    _initializeCamera();
  }

  Future<void> _initializeCamera() async {
    setState(() {
      _isLoading = true;
      _errorMessage = '';
    });

    final status = await Permission.camera.request();

    if (status.isGranted) {
      setState(() {
        _isPermissionGranted = true;
      });

      poseService?.dispose();
      poseService = PoseService(onPoseDetected: (landmarks) {
        ExerciseLogic.process(landmarks);
        setState(() {});
      });

      await poseService!.initialize();

      setState(() {
        _isLoading = false;
      });
    } else if (status.isDenied) {
      setState(() {
        _isPermissionGranted = false;
        _isLoading = false;
        _errorMessage = 'Camera permission is required to play the game.';
      });
    } else if (status.isPermanentlyDenied) {
      setState(() {
        _isPermissionGranted = false;
        _isLoading = false;
        _errorMessage = 'Camera permission is permanently denied. Please enable it in app settings.';
      });
    }
  }

  Future<void> _switchCamera() async {
    try {
      await PoseLandmarker.switchCamera();
      final currentCamera = await PoseLandmarker.getCurrentCamera();
      setState(() {
        _cameraFacing = currentCamera == "front" ? 1 : 0;
      });
    } catch (e) {
      // Handle error if needed
    }
  }

  @override
  void dispose() {
    poseService?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _isLoading
          ? const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  CircularProgressIndicator(),
                  SizedBox(height: 16),
                  Text('Initializing camera...'),
                ],
              ),
            )
          : !_isPermissionGranted
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(20.0),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(
                          Icons.camera_alt_outlined,
                          size: 64,
                          color: Colors.grey,
                        ),
                        const SizedBox(height: 16),
                        Text(
                          _errorMessage,
                          textAlign: TextAlign.center,
                          style: const TextStyle(fontSize: 16),
                        ),
                        const SizedBox(height: 20),
                        ElevatedButton(
                          onPressed: () async {
                            if (_errorMessage.contains('permanently')) {
                              await openAppSettings();
                            } else {
                              await _initializeCamera();
                            }
                          },
                          child: Text(
                            _errorMessage.contains('permanently')
                                ? 'Open Settings'
                                : 'Request Permission',
                          ),
                        ),
                      ],
                    ),
                  ),
                )
              : Stack(
                  fit: StackFit.expand,
                  children: [
                    const NativeCameraPreview(),

                    if (poseService?.currentLandmarks != null)
                      CustomPaint(
                        painter: PosePainter(poseService!.currentLandmarks!),
                      ),

                    Positioned(
                      top: 40,
                      right: 20,
                      child: Container(
                        padding: const EdgeInsets.all(8),
                        color: Colors.black54,
                        child: Text(
                          'Score: ${ExerciseLogic.score}',
                          style: const TextStyle(
                              color: Colors.white, fontSize: 22),
                        ),
                      ),
                    ),

                    Positioned(
                      top: 40,
                      left: 20,
                      child: FloatingActionButton(
                        onPressed: _switchCamera,
                        backgroundColor: Colors.black54,
                        child: Icon(
                          _cameraFacing == 1
                              ? Icons.camera_front
                              : Icons.camera_rear,
                          color: Colors.white,
                        ),
                      ),
                    ),
                  ],
                ),
    );
  }
}
