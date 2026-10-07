import { getAuthHeader } from './supabase';
import { API_BASE_URL } from './api';
import type { ParsedTaskSuggestion } from '../types/brainDump';

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

export async function parseDump(id: string): Promise<ParsedTaskSuggestion> {
  const headers = await getAuthHeader();
  const response = await fetch(
    API_BASE_URL + '/api/braindump/' + encodeURIComponent(id) + '/parse',
    { method: 'POST', headers },
  );
  if (!response.ok) throw new Error('Failed to parse brain dump');
  const result: { suggestions: ParsedTaskSuggestion[] } = await response.json();
  if (!result.suggestions.length) throw new Error('No actionable task was found');
  return result.suggestions[0];
}

export async function convertDumpToTask(
  id: string,
  suggestion: ParsedTaskSuggestion,
) {
  const headers = await getAuthHeader();
  const response = await fetch(
    API_BASE_URL + '/api/braindump/' + encodeURIComponent(id) + '/convert',
    {
      method: 'POST',
      headers,
      body: JSON.stringify({ suggestions: [suggestion] }),
    },
  );
  if (!response.ok) throw new Error('Failed to convert brain dump');
  return response.json();
}
