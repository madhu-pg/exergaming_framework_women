import 'package:flutter/material.dart';
import '../models/session_data.dart';
import '../models/difficulty_config.dart';
import 'instructions_screen.dart';

class BenefitsScreen extends StatelessWidget {
  final SessionData sessionData;
  final DifficultyConfig config;

  const BenefitsScreen({
    super.key,
    required this.sessionData,
    required this.config,
  });

  String _getBenefitImage() {
    // Map exercise types to their benefit background images
    final prefix = sessionData.fitnessType == 'sedentary' ? 'sed' : 'pcod';
    final type = sessionData.exerciseType;
    final key = '${prefix}_$type';

    switch (key) {
      case 'sed_cardio':
        return 'assets/images/backgrounds/img6.png';
      // Future: add more mappings as images are added
      // case 'sed_strength': return 'assets/images/backgrounds/img7.png';
      // case 'sed_stretch': return 'assets/images/backgrounds/img8.png';
      // case 'pcod_cardio': return 'assets/images/backgrounds/img9.png';
      // case 'pcod_strength': return 'assets/images/backgrounds/img10.png';
      // case 'pcod_stretch': return 'assets/images/backgrounds/img11.png';
      default:
        return 'assets/images/backgrounds/img6.png';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        fit: StackFit.expand,
        children: [
          Image.asset(
            _getBenefitImage(),
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
                          Navigator.of(context).push(
                            MaterialPageRoute(
                              builder: (_) => InstructionsScreen(
                                sessionData: sessionData,
                                config: config,
                              ),
                            ),
                          );
                        },
                        style: _buttonStyle(),
                        child: const Text('Next',
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
