import { getAuthHeader } from './supabase';
import { API_BASE_URL } from './api';

export async function createBrainDump(content: string) {
  const headers = await getAuthHeader();
  const response = await fetch(`${API_BASE_URL}/api/braindump`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ content }),
  });
  if (!response.ok) throw new Error('Failed to save brain dump');
  return response.json();
}

export async function getBrainDumps() {
  const headers = await getAuthHeader();
  const response = await fetch(`${API_BASE_URL}/api/braindump`, { headers });
  if (!response.ok) throw new Error('Failed to load brain dumps');
  return response.json();
}

export async function convertBrainDump(id: string) {
  const headers = await getAuthHeader();
  const response = await fetch(`${API_BASE_URL}/api/braindump/${id}/convert`, {
    method: 'POST',
    headers,
  });
  if (!response.ok) throw new Error('Failed to convert brain dump');
  return response.json();
}
