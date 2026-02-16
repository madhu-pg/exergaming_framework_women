class DifficultyConfig {
  final int totalSets;
  final int setDurationSeconds;
  final int restDurationSeconds;
  final int pointsPerSet;
  final int maxScore;
  final int growthThreshold;
  final int cooldownFrames;

  const DifficultyConfig({
    required this.totalSets,
    required this.setDurationSeconds,
    required this.restDurationSeconds,
    required this.pointsPerSet,
    required this.maxScore,
    required this.growthThreshold,
    required this.cooldownFrames,
  });

  static const easy = DifficultyConfig(
    totalSets: 3,
    setDurationSeconds: 120,
    restDurationSeconds: 45,
    pointsPerSet: 12,
    maxScore: 36,
    growthThreshold: 3,
    cooldownFrames: 20,
  );

  static const medium = DifficultyConfig(
    totalSets: 4,
    setDurationSeconds: 120,
    restDurationSeconds: 40,
    pointsPerSet: 12,
    maxScore: 48,
    growthThreshold: 3,
    cooldownFrames: 20,
  );

  static const hard = DifficultyConfig(
    totalSets: 5,
    setDurationSeconds: 150,
    restDurationSeconds: 30,
    pointsPerSet: 12,
    maxScore: 60,
    growthThreshold: 3,
    cooldownFrames: 20,
  );

  static DifficultyConfig fromString(String difficulty) {
    switch (difficulty) {
      case 'medium':
        return medium;
      case 'hard':
        return hard;
      default:
        return easy;
    }
  }
}
