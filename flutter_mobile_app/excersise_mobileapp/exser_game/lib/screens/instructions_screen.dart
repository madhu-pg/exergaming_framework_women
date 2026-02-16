import 'package:flutter/material.dart';
import '../models/session_data.dart';
import '../models/difficulty_config.dart';
import 'cardio_game_screen.dart';

class InstructionsScreen extends StatelessWidget {
  final SessionData sessionData;
  final DifficultyConfig config;

  const InstructionsScreen({
    super.key,
    required this.sessionData,
    required this.config,
  });

  String _getInstructionImage() {
    final prefix = sessionData.fitnessType == 'sedentary' ? 'sed' : 'pcod';
    final type = sessionData.exerciseType;
    final key = '${prefix}_$type';

    switch (key) {
      case 'sed_cardio':
        return 'assets/images/backgrounds/img12.png';
      // Future: add more mappings
      // case 'sed_strength': return 'assets/images/backgrounds/img13.png';
      // case 'sed_stretch': return 'assets/images/backgrounds/img14.png';
      // case 'pcod_cardio': return 'assets/images/backgrounds/img15.png';
      // case 'pcod_strength': return 'assets/images/backgrounds/img16.png';
      // case 'pcod_stretch': return 'assets/images/backgrounds/img17.png';
      default:
        return 'assets/images/backgrounds/img12.png';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        fit: StackFit.expand,
        children: [
          Image.asset(
            _getInstructionImage(),
            fit: BoxFit.cover,
          ),
          SafeArea(
            child: Column(
              children: [
                const Spacer(),
                Padding(
                  padding: const EdgeInsets.all(20),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      ElevatedButton(
                        onPressed: () => Navigator.pop(context),
                        style: _buttonStyle(),
                        child: const Text('Back',
                            style: TextStyle(
                                fontSize: 18, fontWeight: FontWeight.bold)),
                      ),
                      ElevatedButton(
                        onPressed: () {
                          Navigator.of(context).pushReplacement(
                            MaterialPageRoute(
                              builder: (_) => CardioGameScreen(
                                sessionData: sessionData,
                                config: config,
                              ),
                            ),
                          );
                        },
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.green.shade600,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(
                              horizontal: 32, vertical: 14),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(10),
                            side: const BorderSide(
                                color: Colors.green, width: 2),
                          ),
                        ),
                        child: const Text('Start Game',
                            style: TextStyle(
                                fontSize: 18, fontWeight: FontWeight.bold)),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  ButtonStyle _buttonStyle() {
    return ElevatedButton.styleFrom(
      backgroundColor: Colors.white,
      foregroundColor: Colors.black,
      padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 14),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: const BorderSide(color: Colors.black, width: 2),
      ),
    );
  }
}
