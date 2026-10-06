const MORNING_PROMPTS = [
  "You don't have to do everything today. Just take the next step.",
  "Small steps create big changes. Let's make today count.",
  "Progress isn't about being perfect, it's about showing up.",
  "One task at a time. You've got this.",
];

const EVENING_PROMPTS_LOW_MOOD = [
  "Thanks for checking in. Let's make the next step a little easier.",
  "Some days are just harder. That's okay — you're still here.",
];

const EVENING_PROMPTS_OKAY_MOOD = ["Every day doesn't have to be your best day. You showed up."];

const EVENING_PROMPTS_GOOD_MOOD = [
  "You're doing great! Keep showing up. You got this.",
  'Nice work today. Let that carry into tomorrow.',
];

function pickRotating(pool: string[]): string {
  // Rotates by day-of-year so it's stable for the whole day, not random per render.
  const dayOfYear = Math.floor(
    (Date.now() - new Date(new Date().getFullYear(), 0, 0).getTime()) / 86400000,
  );
  return pool[dayOfYear % pool.length];
}

export function getMorningPrompt(): string {
  return pickRotating(MORNING_PROMPTS);
}

// mood: 1-5, matching the existing check-in mood scale
export function getEveningPrompt(mood?: number): string {
  if (mood === undefined) return pickRotating(EVENING_PROMPTS_OKAY_MOOD);
  if (mood <= 2) return pickRotating(EVENING_PROMPTS_LOW_MOOD);
  if (mood === 3) return pickRotating(EVENING_PROMPTS_OKAY_MOOD);
  return pickRotating(EVENING_PROMPTS_GOOD_MOOD);
}

export function getMascotVariantForMood(mood?: number): 'neutral' | 'supportive' {
  if (mood !== undefined && mood <= 2) return 'supportive';
  return 'neutral';
}
