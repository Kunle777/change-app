import { getAuthHeader } from './supabase';
import { API_BASE_URL } from './api';

export async function sendAIMessage(message: string) {
  const headers = await getAuthHeader();
  const response = await fetch(`${API_BASE_URL}/api/ai/chat`, {
    method: 'POST',
    headers: {
      ...headers,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ message }),
  });

  if (response.status === 429) {
    throw new Error('Daily AI limit reached — resets tomorrow');
  }

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error((err as any).detail || "Couldn't reach ELVYN right now.");
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
