import { API_BASE_URL } from './api';
import { getAuthHeader } from './supabase';

export type ActivityStreak = {
  current_streak: number;
  longest_streak: number;
  last_active_date: string | null;
  timezone: string | null;
};

function deviceTimezone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || 'Africa/Lagos';
}

export async function recordDailyActivity(): Promise<ActivityStreak> {
  const response = await fetch(`${API_BASE_URL}/api/users/activity`, {
    method: 'POST',
    headers: { ...(await getAuthHeader()), 'Content-Type': 'application/json' },
    body: JSON.stringify({ timezone: deviceTimezone() }),
  });
  if (!response.ok) throw new Error('Could not update activity streak.');
  return response.json();
}

export async function getActivityStreak(): Promise<ActivityStreak> {
  const response = await fetch(`${API_BASE_URL}/api/users/activity`, {
    headers: await getAuthHeader(),
  });
  if (!response.ok) throw new Error('Could not load activity streak.');
  return response.json();
}
