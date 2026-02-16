import 'package:flutter/material.dart';
import '../models/session_data.dart';
import '../models/difficulty_config.dart';
import 'benefits_screen.dart';

class DifficultyScreen extends StatelessWidget {
  final SessionData sessionData;

  const DifficultyScreen({super.key, required this.sessionData});

  String _buildExerciseKey() {
    final prefix =
        sessionData.fitnessType == 'sedentary' ? 'sed' : 'pcod';
    String exercisePart;
    if (sessionData.fitnessType == 'sedentary') {
      switch (sessionData.exerciseType) {
        case 'cardio':
          exercisePart = 'cardio_step_touch';
          break;
        case 'strength':
          exercisePart = 'strength_side_leg';
          break;
        case 'stretch':
          exercisePart = 'stretch_side_stretch';
          break;
        default:
          exercisePart = 'cardio_step_touch';
      }
    } else {
      switch (sessionData.exerciseType) {
        case 'cardio':
          exercisePart = 'cardio_low_march';
          break;
        case 'strength':
          exercisePart = 'strength_squats';
          break;
        case 'stretch':
          exercisePart = 'stretch_spinal_twist';
          break;
        default:
          exercisePart = 'cardio_low_march';
      }
    }
    return '${prefix}_${exercisePart}_${sessionData.difficulty}';
  }

  String _exerciseTitle() {
    final type = sessionData.exerciseType;
    if (sessionData.fitnessType == 'sedentary') {
      switch (type) {
        case 'cardio':
          return 'Cardio: Step Touch';
        case 'strength':
          return 'Strength: Side Leg Raises';
        case 'stretch':
          return 'Stretching: Side Stretch';
      }
    } else {
      switch (type) {
        case 'cardio':
          return 'Cardio: Low-impact Marching';
        case 'strength':
          return 'Strength: Squats';
        case 'stretch':
          return 'Stretch: Spinal Twist';
      }
    }
    return 'Exercise';
  }

  @override
  Widget build(BuildContext context) {
    final difficulties = [
      {'label': 'Easy', 'value': 'easy'},
      {'label': 'Medium', 'value': 'medium'},
      {'label': 'Hard', 'value': 'hard'},
    ];

    return Scaffold(
      body: Stack(
        fit: StackFit.expand,
        children: [
          Image.asset(
            'assets/images/backgrounds/img4.png',
            fit: BoxFit.cover,
          ),
          SafeArea(
            child: Column(
              children: [
                const SizedBox(height: 100),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
                  decoration: BoxDecoration(
                    color: Colors.black.withValues(alpha: 0.5),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    'Select difficulty for:\n${_exerciseTitle()}',
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
                ),
                const SizedBox(height: 30),
                ...difficulties.map((d) => Padding(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 40, vertical: 8),
                      child: SizedBox(
                        width: double.infinity,
                        child: ElevatedButton(
                          onPressed: () {
                            sessionData.difficulty = d['value']!;
                            sessionData.exerciseKey = _buildExerciseKey();
                            Navigator.of(context).push(
                              MaterialPageRoute(
                                builder: (_) => BenefitsScreen(
                                  sessionData: sessionData,
                                  config: DifficultyConfig.fromString(
                                      d['value']!),
                                ),
                              ),
                            );
                          },
                          style: ElevatedButton.styleFrom(
                            backgroundColor:
                                Colors.white.withValues(alpha: 0.9),
                            foregroundColor: Colors.black,
                            padding: const EdgeInsets.symmetric(
                                horizontal: 20, vertical: 18),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(10),
                              side: const BorderSide(
                                  color: Colors.black, width: 3),
                            ),
                          ),
                          child: Text(
                            d['label']!,
                            style: const TextStyle(
                              fontSize: 20,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      ),
                    )),
                const Spacer(),
                Padding(
                  padding: const EdgeInsets.all(20),
                  child: Align(
                    alignment: Alignment.bottomLeft,
                    child: ElevatedButton(
                      onPressed: () => Navigator.pop(context),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.white,
                        foregroundColor: Colors.black,
                        padding: const EdgeInsets.symmetric(
                            horizontal: 32, vertical: 14),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10),
                          side:
                              const BorderSide(color: Colors.black, width: 2),
                        ),
                      ),
                      child: const Text('Back',
                          style: TextStyle(
                              fontSize: 18, fontWeight: FontWeight.bold)),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
