import 'dart:async';
import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_mp_pose_landmarker/flutter_mp_pose_landmarker.dart';
import 'package:permission_handler/permission_handler.dart';
import '../pose/pose_service.dart';
import '../pose/pose_painter.dart';
import '../logic/exercise_logic.dart';
import '../models/session_data.dart';
import '../models/difficulty_config.dart';
import '../utils/feedback_utils.dart';
import 'results_screen.dart';

class CardioGameScreen extends StatefulWidget {
  final SessionData sessionData;
  final DifficultyConfig config;

  const CardioGameScreen({
    super.key,
    required this.sessionData,
    required this.config,
  });

  @override
  State<CardioGameScreen> createState() => _CardioGameScreenState();
}

class _CardioGameScreenState extends State<CardioGameScreen> {
  // Camera & pose
  PoseService? _poseService;
  bool _isPermissionGranted = false;
  bool _isLoading = true;

  // Game state
  final CardioExerciseLogic _exerciseLogic = CardioExerciseLogic();
  late List<int> _setScores;
  int _totalScore = 0;
  int _currentSet = 1;
  int _plantIndex = 0;
  bool _isResting = false;
  bool _setCompleted = false;
  bool _gameFinished = false;

  // Timing
  DateTime? _setStartTime;
  DateTime? _restStartTime;
  DateTime _lastScoreTime = DateTime(2000);
  Timer? _gameTimer;

  // Audio
  final AudioPlayer _audioPlayer = AudioPlayer();

  @override
  void initState() {
    super.initState();
    _setScores = List.filled(widget.config.totalSets, 0);
    _initializeCamera();
  }

  Future<void> _initializeCamera() async {
    final status = await Permission.camera.request();
    if (status.isGranted) {
      setState(() => _isPermissionGranted = true);

      _poseService = PoseService(onPoseDetected: _onPoseDetected);
      await _poseService!.initialize();

      setState(() => _isLoading = false);

      // Start the game loop
      _setStartTime = DateTime.now();
      _gameTimer = Timer.periodic(
        const Duration(milliseconds: 33),
        (_) => _gameLoop(),
      );
    } else {
      setState(() {
        _isPermissionGranted = false;
        _isLoading = false;
      });
    }
  }

  void _onPoseDetected(List<PoseLandmarkPoint> landmarks) {
    if (_isResting || _gameFinished) return;
    if (_setCompleted) return;

    final scored = _exerciseLogic.process(landmarks, widget.config);
    if (scored) {
      final setIdx = _currentSet - 1;
      if (_setScores[setIdx] < widget.config.pointsPerSet) {
        _setScores[setIdx]++;
        _totalScore++;
        _plantIndex++;
        _lastScoreTime = DateTime.now();

        // Play sound
        _audioPlayer.play(AssetSource('sounds/correct.mp3'));

        // Check if set score maxed out
        if (_setScores[setIdx] >= widget.config.pointsPerSet) {
          _setCompleted = true;
        }
      }
    }
    if (mounted) setState(() {});
  }

  void _gameLoop() {
    if (!mounted || _gameFinished) return;

    final now = DateTime.now();

    if (_isResting) {
      final restElapsed =
          now.difference(_restStartTime!).inMilliseconds / 1000.0;
      final restRemaining =
          widget.config.restDurationSeconds - restElapsed;

      if (restRemaining <= 0) {
        // End rest, start next set
        _isResting = false;
        _plantIndex = 0;
        _exerciseLogic.reset();
        _currentSet++;
        _setStartTime = now;
        _setCompleted = false;
      }
      setState(() {});
      return;
    }

    if (_setStartTime == null) return;

    final elapsed =
        now.difference(_setStartTime!).inMilliseconds / 1000.0;
    final remaining = widget.config.setDurationSeconds - elapsed;

    // End set if time up or score completed
    if (remaining <= 0 || _setCompleted) {
      _setCompleted = false;

      if (_currentSet < widget.config.totalSets) {
        // Start rest period
        _isResting = true;
        _restStartTime = now;
      } else {
        // Game finished
        _gameFinished = true;
        _gameTimer?.cancel();
        _navigateToResults();
      }
    }

    setState(() {});
  }

  void _navigateToResults() {
    Future.delayed(const Duration(milliseconds: 100), () {
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (_) => ResultsScreen(
            sessionData: widget.sessionData,
            config: widget.config,
            totalScore: _totalScore,
            setScores: _setScores,
          ),
        ),
      );
    });
  }

  @override
  void dispose() {
    _gameTimer?.cancel();
    _poseService?.dispose();
    _audioPlayer.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        backgroundColor: Colors.black,
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              CircularProgressIndicator(color: Colors.white),
              SizedBox(height: 16),
              Text('Initializing camera...',
                  style: TextStyle(color: Colors.white, fontSize: 18)),
            ],
          ),
        ),
      );
    }

    if (!_isPermissionGranted) {
      return Scaffold(
        backgroundColor: Colors.black,
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.camera_alt_outlined,
                  size: 64, color: Colors.grey),
              const SizedBox(height: 16),
              const Text(
                'Camera permission is required to play.',
                style: TextStyle(color: Colors.white, fontSize: 16),
              ),
              const SizedBox(height: 20),
              ElevatedButton(
                onPressed: () => openAppSettings(),
                child: const Text('Open Settings'),
              ),
            ],
          ),
        ),
      );
    }

    final screenWidth = MediaQuery.of(context).size.width;
    final screenHeight = MediaQuery.of(context).size.height;
    final cameraWidth = screenWidth * 0.35;
    final cameraHeight = cameraWidth * 0.75;

    // Calculate timer values
    double remaining = 0;
    if (!_isResting && _setStartTime != null) {
      final elapsed =
          DateTime.now().difference(_setStartTime!).inMilliseconds / 1000.0;
      remaining =
          (widget.config.setDurationSeconds - elapsed).clamp(0, double.infinity);
    }
    final mins = remaining.toInt() ~/ 60;
    final secs = remaining.toInt() % 60;

    // Camera border color
    final isRecentlyScored =
        DateTime.now().difference(_lastScoreTime).inMilliseconds < 1000;
    final borderColor =
        isRecentlyScored ? Colors.green : const Color(0xFF9400D3);

    // Current set score
    final setIdx = _currentSet - 1;
    final currentSetScore =
        setIdx < _setScores.length ? _setScores[setIdx] : 0;

    // Plant image index (cycle through 9 images)
    final plantImageIndex = (_plantIndex % 9) + 1;

    return Scaffold(
      body: Stack(
        fit: StackFit.expand,
        children: [
          // Layer 1: Game background
          Image.asset(
            'assets/images/game/background.png',
            fit: BoxFit.cover,
          ),

          // Layer 2: Plant image (centered, shifted down by plant growth)
          Positioned(
            left: screenWidth * 0.25,
            right: screenWidth * 0.25,
            top: (screenHeight * 0.25) + 50 + (_plantIndex * 4),
            bottom: screenHeight * 0.1,
            child: Image.asset(
              'assets/images/game/plant_stage$plantImageIndex.png',
              fit: BoxFit.contain,
            ),
          ),

          // Layer 3: Camera preview (small, top-left)
          Positioned(
            left: 10,
            top: 10,
            child: Container(
              width: cameraWidth,
              height: cameraHeight,
              decoration: BoxDecoration(
                border: Border.all(color: borderColor, width: 4),
              ),
              child: ClipRect(
                child: SizedBox(
                  width: cameraWidth,
                  height: cameraHeight,
                  child: const AndroidView(
                    viewType: 'camera_preview_view',
                    layoutDirection: TextDirection.ltr,
                  ),
                ),
              ),
            ),
          ),

          // Layer 4: Pose overlay on camera
          if (_poseService?.currentLandmarks != null)
            Positioned(
              left: 10,
              top: 10,
              child: SizedBox(
                width: cameraWidth,
                height: cameraHeight,
                child: CustomPaint(
                  painter: PosePainter(_poseService!.currentLandmarks!),
                ),
              ),
            ),

          // Layer 5: Timer display (top center)
          Positioned(
            top: 15,
            left: cameraWidth + 20,
            right: 10,
            child: Center(
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                decoration: BoxDecoration(
                  color: Colors.black.withValues(alpha: 0.7),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  'Set $_currentSet - ${mins.toString().padLeft(2, '0')}:${secs.toString().padLeft(2, '0')}',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 22,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ),
          ),

          // Layer 6: Score display (below timer, top right area)
          Positioned(
            top: 60,
            right: 10,
            child: Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: const Color.fromRGBO(10, 30, 80, 0.86),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                'Set Score: $currentSetScore/${widget.config.pointsPerSet} | Set $_currentSet',
                style: const TextStyle(
                  color: Color(0xFFD4AF37), // Gold
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),

          // Rest overlay
          if (_isResting) _buildRestOverlay(),
        ],
      ),
    );
  }

  Widget _buildRestOverlay() {
    final restElapsed = _restStartTime != null
        ? DateTime.now().difference(_restStartTime!).inMilliseconds / 1000.0
        : 0.0;
    final restRemaining =
        (widget.config.restDurationSeconds - restElapsed).clamp(0, double.infinity);
    final setIdx = _currentSet - 1;
    final setScore = setIdx < _setScores.length ? _setScores[setIdx] : 0;
    final feedback = getSetFeedback(setScore);

    return Container(
      color: Colors.black.withValues(alpha: 0.85),
      child: Center(
        child: Container(
          margin: const EdgeInsets.symmetric(horizontal: 30),
          padding: const EdgeInsets.all(30),
          decoration: BoxDecoration(
            color: const Color.fromRGBO(0, 0, 50, 0.9),
            borderRadius: BorderRadius.circular(16),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Set $_currentSet Complete!',
                style: const TextStyle(
                  color: Color(0xFFFFA500), // Orange
                  fontSize: 32,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 20),
              Text(
                'Set $_currentSet Score: $setScore/${widget.config.pointsPerSet}',
                style: const TextStyle(
                  color: Color(0xFF00F000), // Bright green
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 16),
              Text(
                feedback,
                style: const TextStyle(
                  color: Color(0xFFFFD700), // Gold
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 24),
              Text(
                'Set ${_currentSet + 1} starts in...',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 10),
              Text(
                '${restRemaining.toInt()}s',
                style: const TextStyle(
                  color: Colors.yellow,
                  fontSize: 48,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 16),
              const Text(
                'Get ready for next set - REST',
                style: TextStyle(
                  color: Color(0xFFDCDCDC), // Light gray
                  fontSize: 16,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
