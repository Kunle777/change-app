import {
  ANTI_PROCRASTINATION_PROMPTS,
  EVENING_FINE_MOOD_PROMPTS,
  EVENING_LOW_MOOD_PROMPTS,
  MORNING_PROMPTS,
} from '../data/prompts';

const LOW_MOOD_RESPONSES = [
  'Thanks for checking in. You do not have to figure everything out right now.',
  'A hard moment does not define your whole day. Take this one step at a time.',
  'It is okay to meet yourself where you are today.',
  'You deserve patience on the days that take more out of you.',
  'Thanks for being honest with yourself. What you need can be small and simple.',
  'You showed up for this check-in. Let that be enough for this moment.',
  'There is no need to force a bright side. Be gentle with yourself instead.',
  'Some days call for a softer pace. It is okay to take one.',
  'You can take a pause before deciding what comes next.',
  'You do not have to earn rest by finishing everything.',
  'One small need at a time is enough to focus on.',
  'It is okay if today is about getting through, not getting ahead.',
  'You are allowed to ask for support, even when you are not sure what to say.',
  'A difficult feeling deserves care, not criticism.',
  'You can choose a smaller expectation for yourself today.',
  'Thanks for checking in. Take the next moment at your own pace.',
];

const OKAY_MOOD_RESPONSES = [
  'Thanks for checking in. An ordinary day is enough.',
  'You do not need to feel amazing to take a small step forward.',
  'Not every day needs a big breakthrough. Keep going at your own pace.',
  'It sounds like today has a bit of everything. Make space for what you need.',
  'You made time to notice how you are doing. That counts.',
  'Take the next part of your day one thing at a time.',
  'You can decide what matters most from here, one step at a time.',
  'A little progress or a little rest can both be worthwhile.',
  'It is okay to have mixed feelings about how today is going.',
  'What you have capacity for today is enough to start with.',
  'Thanks for making a moment to check in with yourself.',
  'You do not need to turn an okay day into a perfect one.',
  'Notice what you need next, then give yourself permission to do that.',
  'There is room for your day to change from here.',
];

const GOOD_MOOD_RESPONSES = [
  'Glad there is some good in today. Enjoy it at your own pace.',
  'Thanks for sharing that. What is one thing you would like to carry into the rest of your day?',
  'Good to hear. Take a moment to notice what is helping.',
  'That is lovely to hear. You can build on it one step at a time.',
  'Let yourself enjoy this moment without needing to make it last forever.',
  'A little momentum can be useful. Choose what feels right to do next.',
  'Thanks for checking in. Keep room for rest as well as the good energy.',
  'It is nice to have a day with some ease in it.',
  'Let yourself enjoy what is going well, without needing to explain it.',
  'You can use this energy for something meaningful or simply enjoy the moment.',
  'Good days can include breaks too. Keep a little space for yourself.',
  'It is great that you noticed how you are feeling.',
  'What is working today may be worth remembering for another day.',
  'Take the win, even if it is a small one.',
  'I am glad you have some good energy to work with today.',
  'Keep choosing what feels useful and kind to you.',
];

function dayIndex(date: Date): number {
  return Math.floor(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()) / 86_400_000);
}

function pickForDay(items: string[], date: Date, offset = 0): string {
  const index = ((dayIndex(date) + offset) % items.length + items.length) % items.length;
  return items[index];
}

/** Returns the same response for the same mood during a calendar day. */
export function getCheckInResponse(mood: number, date = new Date()): string {
  if (!Number.isFinite(mood)) return pickForDay(OKAY_MOOD_RESPONSES, date);
  if (mood <= 2) return pickForDay(LOW_MOOD_RESPONSES, date);
  if (mood === 3) return pickForDay(OKAY_MOOD_RESPONSES, date, 3);
  return pickForDay(GOOD_MOOD_RESPONSES, date, 5);
}

/** Selects a gentle daily prompt without changing it on each component render. */
export function getCheckInPrompt(type: 'morning' | 'evening', mood: number | null, date = new Date()): string {
  if (type === 'morning') {
    const prompts = mood !== null && mood <= 2
      ? [...EVENING_LOW_MOOD_PROMPTS, ...MORNING_PROMPTS]
      : mood !== null && mood >= 4
        ? [...MORNING_PROMPTS, ...ANTI_PROCRASTINATION_PROMPTS]
        : MORNING_PROMPTS;
    return pickForDay(prompts, date, mood ?? 0);
  }

  const prompts = mood !== null && mood <= 2 ? EVENING_LOW_MOOD_PROMPTS : EVENING_FINE_MOOD_PROMPTS;
  return pickForDay(prompts, date, mood ?? 0);
}

/** A low-pressure nudge for users who want help getting started. */
export function getStartingPrompt(date = new Date()): string {
  return pickForDay(ANTI_PROCRASTINATION_PROMPTS, date);
}
