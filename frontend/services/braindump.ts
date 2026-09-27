import { getAuthHeader } from './supabase';
import { API_BASE_URL } from './api';
import type { BrainDump, ParsedTaskSuggestion } from '../types/brainDump';
import type { Task } from '../types/task';
export type { ParsedTaskSuggestion } from '../types/brainDump';

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

export async function createBrainDump(
  content: string,
  source: 'text' | 'voice' = 'text',
): Promise<BrainDump> {
  return requestJson('/api/braindump', {
    method: 'POST',
    body: JSON.stringify({ content, source }),
    headers: { 'Content-Type': 'application/json' },
  });
}

export async function getBrainDumps(): Promise<BrainDump[]> {
  return requestJson('/api/braindump');
}

export async function getRecentDumps(): Promise<BrainDump[]> {
  return getBrainDumps();
}

export async function parseBrainDump(id: string): Promise<ParsedTaskSuggestion[]> {
  const result = await requestJson(`/api/braindump/${id}/parse`, { method: 'POST' });
  return result.suggestions;
}

export async function convertBrainDump(
  id: string,
  suggestions: ParsedTaskSuggestion[],
): Promise<Task[]> {
  return requestJson(`/api/braindump/${id}/convert`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ suggestions }),
  });
}

export async function parseDump(id: string): Promise<ParsedTaskSuggestion | null> {
  const suggestions = await parseBrainDump(id);
  return suggestions[0] ?? null;
}

export async function convertDumpToTask(
  id: string,
  suggestion: ParsedTaskSuggestion,
): Promise<Task | null> {
  const tasks = await convertBrainDump(id, [suggestion]);
  return tasks[0] ?? null;
}
