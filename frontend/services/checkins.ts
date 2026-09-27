import { getAuthHeader } from './supabase';
import { API_BASE_URL } from './api'; // your existing runtime base-URL detector

//connects to the backend
//function to get morning checkin from the backend
export async function submitMorningCheckin(mood: number, goalToday?: string) {
  const headers = await getAuthHeader();
  const response = await fetch(`${API_BASE_URL}/api/checkins/morning`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ mood, ...(goalToday ? { goal_today: goalToday } : {}) }),
  });
  if (!response.ok) throw new Error('Failed to submit morning check-in');
  return response.json();
}

//evening checkin
export async function submitEveningCheckin(
  mood: number,
  reflection: string,
  goalStatus: string | null,
) {
  const headers = await getAuthHeader();
  const response = await fetch(`${API_BASE_URL}/api/checkins/evening`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ mood, reflection, goal_status: goalStatus }),
  });
  if (!response.ok) throw new Error('Failed to submit evening check-in');
  return response.json();
}

export type FullCheckInPayload = {
  mood: number;
  goal_today?: string;
  goal_status?: string;
  reflection?: string;
};

export async function submitFullCheckIn(
  type: 'morning' | 'evening',
  payload: FullCheckInPayload,
) {
  if (type === 'morning') {
    return submitMorningCheckin(payload.mood, payload.goal_today);
  }

  return submitEveningCheckin(
    payload.mood,
    payload.reflection ?? '',
    payload.goal_status ?? null,
  );
}

export async function getTodayCheckinStatus(): Promise<{
  checkins_enabled: boolean;
  morning_done: boolean;
  evening_done: boolean;
}> {
  const headers = await getAuthHeader();
  const response = await fetch(`${API_BASE_URL}/api/checkins/today-status`, { headers });
  if (!response.ok) throw new Error('Failed to fetch check-in status');
  return response.json();
}
