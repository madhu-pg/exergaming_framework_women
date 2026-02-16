class SessionData {
  String name;
  String age;
  String heightCm;
  String weightKg;
  String fitnessType; // "sedentary" or "pcod"
  String exerciseType; // "cardio", "strength", "stretch"
  String difficulty; // "easy", "medium", "hard"
  String exerciseKey; // e.g., "sed_cardio_step_touch_easy"

  SessionData({
    this.name = '',
    this.age = '',
    this.heightCm = '',
    this.weightKg = '',
    this.fitnessType = '',
    this.exerciseType = '',
    this.difficulty = '',
    this.exerciseKey = '',
  });
}
