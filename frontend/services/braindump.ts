import { getAuthHeader } from './supabase';
import { API_BASE_URL } from './api';

export type ParsedTaskSuggestion = {
  title: string;
  priority: 'low' | 'medium' | 'high';
  recurrence_rule?: {
    frequency: 'daily' | 'weekly' | 'monthly';
    interval: number;
    days_of_week?: number[];
    timezone?: string;
    start_date?: string | null;
    end_date?: string | null;
    occurrence_limit?: number | null;
  } | null;
};

async function requestJson(path: string, init?: RequestInit) {
  const headers = await getAuthHeader();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { ...headers, ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? 'Brain dump request failed');
  }
  return response.json();
}

export async function createBrainDump(content: string) {
  return requestJson('/api/braindump', {
    method: 'POST',
    body: JSON.stringify({ content }),
    headers: { 'Content-Type': 'application/json' },
  });
}

export async function getBrainDumps() {
  return requestJson('/api/braindump');
}

export async function parseBrainDump(id: string): Promise<ParsedTaskSuggestion[]> {
  const result = await requestJson(`/api/braindump/${id}/parse`, { method: 'POST' });
  return result.suggestions;
}

export async function convertBrainDump(
  id: string,
  suggestions: ParsedTaskSuggestion[],
) {
  return requestJson(`/api/braindump/${id}/convert`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ suggestions }),
  });
}
