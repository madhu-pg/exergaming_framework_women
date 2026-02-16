import 'package:flutter/material.dart';
import '../models/session_data.dart';
import '../models/difficulty_config.dart';
import '../utils/feedback_utils.dart';
import '../services/results_service.dart';
import 'start_screen.dart';

class ResultsScreen extends StatefulWidget {
  final SessionData sessionData;
  final DifficultyConfig config;
  final int totalScore;
  final List<int> setScores;

  const ResultsScreen({
    super.key,
    required this.sessionData,
    required this.config,
    required this.totalScore,
    required this.setScores,
  });

  @override
  State<ResultsScreen> createState() => _ResultsScreenState();
}

class _ResultsScreenState extends State<ResultsScreen> {
  bool _saved = false;

  @override
  void initState() {
    super.initState();
    _saveResults();
  }

  Future<void> _saveResults() async {
    if (_saved) return;
    _saved = true;

    final feedback =
        getFinalFeedback(widget.totalScore, widget.config.maxScore);
    try {
      await ResultsService.saveResult(
        session: widget.sessionData,
        score: widget.totalScore,
        feedback: feedback,
      );
    } catch (e) {
      debugPrint('Failed to save results: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final feedback =
        getFinalFeedback(widget.totalScore, widget.config.maxScore);

    return Scaffold(
      body: Stack(
        fit: StackFit.expand,
        children: [
          // Background
          Image.asset(
            'assets/images/game/background.png',
            fit: BoxFit.cover,
          ),

          // Dark overlay panel
          Center(
            child: Container(
              margin: const EdgeInsets.symmetric(horizontal: 30),
              padding: const EdgeInsets.all(30),
              decoration: BoxDecoration(
                color: const Color.fromRGBO(20, 20, 20, 0.88),
                borderRadius: BorderRadius.circular(16),
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text(
                    'Cardio Workout Complete!',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 28,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 24),

                  // Total score
                  Text(
                    'Total Score: ${widget.totalScore}/${widget.config.maxScore}',
                    style: const TextStyle(
                      color: Color(0xFF00FF00), // Bright green
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 16),

                  // Per-set scores
                  ...List.generate(widget.setScores.length, (i) {
                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Text(
                        'Set ${i + 1}: ${widget.setScores[i]}/${widget.config.pointsPerSet}  -  ${getSetFeedback(widget.setScores[i])}',
                        style: const TextStyle(
                          color: Colors.white70,
                          fontSize: 16,
                        ),
                      ),
                    );
                  }),

                  const SizedBox(height: 20),

                  // Final feedback
                  Text(
                    feedback,
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      color: Color(0xFFD4AF37), // Gold
                      fontSize: 22,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 30),

                  // Back to menu button
                  ElevatedButton(
                    onPressed: () {
                      Navigator.of(context).pushAndRemoveUntil(
                        MaterialPageRoute(
                          builder: (_) => const StartScreen(),
                        ),
                        (route) => false,
                      );
                    },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.white,
                      foregroundColor: Colors.black,
                      padding: const EdgeInsets.symmetric(
                          horizontal: 40, vertical: 14),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10),
                        side:
                            const BorderSide(color: Colors.black, width: 2),
                      ),
                    ),
                    child: const Text(
                      'Back to Menu',
                      style: TextStyle(
                          fontSize: 18, fontWeight: FontWeight.bold),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
