import 'package:flutter/material.dart';
import 'screens/start_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const ExerGameApp());
}

class ExerGameApp extends StatelessWidget {
  const ExerGameApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        primarySwatch: Colors.purple,
      ),
      home: const StartScreen(),
    );
  }
}
