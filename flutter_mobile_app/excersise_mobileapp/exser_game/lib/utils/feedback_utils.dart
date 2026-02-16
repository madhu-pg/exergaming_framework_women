String getSetFeedback(int score) {
  if (score <= 3) return "Getting started";
  if (score <= 7) return "Good effort";
  if (score <= 10) return "Strong performance";
  return "Excellent set!";
}

String getFinalFeedback(int totalScore, int maxScore) {
  if (maxScore == 0) return "No data";
  final ratio = totalScore / maxScore;
  if (ratio <= 0.25) return "Needs more practice";
  if (ratio <= 0.50) return "Fair performance";
  if (ratio <= 0.75) return "Good cardio endurance";
  if (ratio <= 0.917) return "Excellent workout performance";
  return "Perfect workout - outstanding!";
}
