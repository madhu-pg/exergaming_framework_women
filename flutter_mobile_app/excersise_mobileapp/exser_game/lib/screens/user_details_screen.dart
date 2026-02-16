import 'package:flutter/material.dart';
import '../models/session_data.dart';
import 'fitness_type_screen.dart';

class UserDetailsScreen extends StatefulWidget {
  final SessionData sessionData;

  const UserDetailsScreen({super.key, required this.sessionData});

  @override
  State<UserDetailsScreen> createState() => _UserDetailsScreenState();
}

class _UserDetailsScreenState extends State<UserDetailsScreen> {
  final _nameController = TextEditingController();
  final _ageController = TextEditingController();
  final _heightController = TextEditingController();
  final _weightController = TextEditingController();
  final _formKey = GlobalKey<FormState>();

  @override
  void initState() {
    super.initState();
    _nameController.text = widget.sessionData.name;
    _ageController.text = widget.sessionData.age;
    _heightController.text = widget.sessionData.heightCm;
    _weightController.text = widget.sessionData.weightKg;
  }

  @override
  void dispose() {
    _nameController.dispose();
    _ageController.dispose();
    _heightController.dispose();
    _weightController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        fit: StackFit.expand,
        children: [
          Image.asset(
            'assets/images/backgrounds/img2.png',
            fit: BoxFit.cover,
          ),
          Center(
            child: SingleChildScrollView(
              child: Container(
                margin: const EdgeInsets.symmetric(horizontal: 30),
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.85),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: Colors.black26, width: 2),
                ),
                child: Form(
                  key: _formKey,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Center(
                        child: Text(
                          'Enter Details',
                          style: TextStyle(
                            fontSize: 24,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                      const SizedBox(height: 20),
                      _buildField('Name', _nameController,
                          TextInputType.text, 'Enter full name'),
                      const SizedBox(height: 16),
                      _buildField('Age', _ageController,
                          TextInputType.number, 'Age'),
                      const SizedBox(height: 16),
                      _buildField('Height (cm)', _heightController,
                          TextInputType.number, 'Height in cm'),
                      const SizedBox(height: 16),
                      _buildField('Weight (kg)', _weightController,
                          TextInputType.number, 'Weight in kg'),
                      const SizedBox(height: 24),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                        children: [
                          _navButton('Back', () => Navigator.pop(context)),
                          _navButton('Next', () {
                            if (_formKey.currentState!.validate()) {
                              widget.sessionData.name =
                                  _nameController.text.trim();
                              widget.sessionData.age =
                                  _ageController.text.trim();
                              widget.sessionData.heightCm =
                                  _heightController.text.trim();
                              widget.sessionData.weightKg =
                                  _weightController.text.trim();
                              Navigator.of(context).push(
                                MaterialPageRoute(
                                  builder: (_) => FitnessTypeScreen(
                                    sessionData: widget.sessionData,
                                  ),
                                ),
                              );
                            }
                          }),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildField(String label, TextEditingController controller,
      TextInputType type, String hint) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label,
            style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
        const SizedBox(height: 4),
        TextFormField(
          controller: controller,
          keyboardType: type,
          decoration: InputDecoration(
            hintText: hint,
            filled: true,
            fillColor: Colors.white,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
            ),
            contentPadding:
                const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
          ),
          validator: (v) =>
              (v == null || v.trim().isEmpty) ? 'Required' : null,
        ),
      ],
    );
  }

  Widget _navButton(String text, VoidCallback onPressed) {
    return ElevatedButton(
      onPressed: onPressed,
      style: ElevatedButton.styleFrom(
        backgroundColor: Colors.white,
        foregroundColor: Colors.black,
        padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 14),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(10),
          side: const BorderSide(color: Colors.black, width: 2),
        ),
      ),
      child: Text(text,
          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
    );
  }
}
