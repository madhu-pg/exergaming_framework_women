import 'dart:io';
import 'package:csv/csv.dart';
import 'package:path_provider/path_provider.dart';
import 'package:intl/intl.dart';
import '../models/session_data.dart';

class ResultsService {
  static Future<void> saveResult({
    required SessionData session,
    required int score,
    required String feedback,
  }) async {
    final directory = await getApplicationDocumentsDirectory();
    final file = File('${directory.path}/exergame_results.csv');

    final now = DateTime.now();
    final dateStr = DateFormat('yyyy-MM-dd').format(now);
    final timeStr = DateFormat('HH:mm:ss').format(now);

    final row = [
      session.name,
      session.age,
      session.heightCm,
      session.weightKg,
      session.exerciseKey,
      score.toString(),
      feedback,
      dateStr,
      timeStr,
    ];

    final exists = await file.exists();
    if (!exists) {
      const header =
          'Name,Age,Height_cm,Weight_kg,Exercise_Type,Score,Feedback,Date,Time\n';
      await file.writeAsString(header);
    }

    final csvRow = const ListToCsvConverter().convert([row]);
    await file.writeAsString('$csvRow\n', mode: FileMode.append);
  }
}
