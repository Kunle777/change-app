export type StreakEvolution =
  | 'default'
  | 'energetic'
  | 'amber'
  | 'confident'
  | 'special'
  | 'elevated'
  | 'legacy';

/** Progression metadata is kept separate from ElvynMascot's neutral/supportive mood variant. */
export function getStreakEvolution(days: number): StreakEvolution {
  if (days >= 100) return 'legacy';
  if (days >= 60) return 'elevated';
  if (days >= 30) return 'special';
  if (days >= 14) return 'confident';
  if (days >= 7) return 'amber';
  if (days >= 3) return 'energetic';
  return 'default';
}
