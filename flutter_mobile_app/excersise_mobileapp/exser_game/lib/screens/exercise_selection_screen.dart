import 'package:flutter/material.dart';
import '../models/session_data.dart';
import 'difficulty_screen.dart';

class ExerciseSelectionScreen extends StatelessWidget {
  final SessionData sessionData;

  const ExerciseSelectionScreen({super.key, required this.sessionData});

  @override
  Widget build(BuildContext context) {
    final isSedentary = sessionData.fitnessType == 'sedentary';

    final exercises = isSedentary
        ? [
            {'label': 'Cardio: Step touch with arm swings', 'type': 'cardio'},
            {'label': 'Strength: Standing Side leg raises', 'type': 'strength'},
            {'label': 'Stretching: Standing Side Stretch', 'type': 'stretch'},
          ]
        : [
            {'label': 'Cardio: Low-impact marching', 'type': 'cardio'},
            {'label': 'Strength/Resistance: Squats', 'type': 'strength'},
            {'label': 'Stretch: Gentle spinal twist', 'type': 'stretch'},
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
                const SizedBox(height: 160),
                ...exercises.map((ex) => Padding(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 40, vertical: 8),
                      child: SizedBox(
                        width: double.infinity,
                        child: ElevatedButton(
                          onPressed: () {
                            sessionData.exerciseType = ex['type']!;
                            Navigator.of(context).push(
                              MaterialPageRoute(
                                builder: (_) => DifficultyScreen(
                                  sessionData: sessionData,
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
                            ex['label']!,
                            style: const TextStyle(
                              fontSize: 18,
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
