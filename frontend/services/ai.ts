import { getAuthHeader } from './supabase';
import { API_BASE_URL } from './api';

export async function sendChatMessage(message: string) {
  const headers = await getAuthHeader();
  const response = await fetch(`${API_BASE_URL}/api/ai/chat`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ message }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error((err as any).detail || 'AI request failed');
  }
  return response.json();
}

export async function getEveningSummary() {
  const headers = await getAuthHeader();
  const response = await fetch(`${API_BASE_URL}/api/ai/evening-summary`, {
    method: 'POST',
    headers,
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error((err as any).detail || 'Failed to get summary');
  }
  return response.json();
}
