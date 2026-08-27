import { api } from './api';
import { getAuthHeader } from './supabase';

export async function getWins(): Promise<{ wins: any[]; streak: number }> {
  const headers = await getAuthHeader();
  const [winsRes, streakRes] = await Promise.all([
    api.get('/api/wins', { headers }),
    api.get('/api/wins/streak', { headers }),
  ]);
  return { wins: winsRes.data, streak: streakRes.data.streak };
}

export async function createWin(description: string) {
  const headers = await getAuthHeader();
  const response = await api.post('/api/wins', { description }, { headers });
  return response.data;
}
