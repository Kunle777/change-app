import { getAuthHeader } from './supabase';
import { API_BASE_URL } from './api';

export async function toggleCheckins(enabled: boolean) {
  const headers = await getAuthHeader();
  const response = await fetch(`${API_BASE_URL}/api/auth/me/checkins-toggle`, {
    method: 'PATCH',
    headers,
    body: JSON.stringify({ enabled }),
  });
  if (!response.ok) throw new Error('Failed to update setting');
  return response.json();
}
