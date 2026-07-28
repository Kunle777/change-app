import { api } from './api';
import { supabase } from './supabase';

export async function register(email: string, password: string, phone?: string) {
  const response = await api.post('api/auth/register', {
    email,
    password,
    phone,
  });
  return response.data;
}

export async function login(email: string, password: string) {
  const response = await api.post('api/auth/login', { email, password });
  return response.data;
}

export async function getProfile(token: string) {
  const response = await api.get('/api/auth/profile', {
    headers: { Authorization: `Bearer ${token}` },
  });
  return response.data;
}

export async function updateFcmToken(token: string) {
  const { data } = await supabase.auth.getSession();
  const accessToken = data.session?.access_token;
  if (!accessToken) {
    throw new Error('No authenticated session available for FCM token registration.');
  }

  const response = await api.patch(
    '/api/auth/fcm-token',
    { token },
    { headers: { Authorization: `Bearer ${accessToken}` } },
  );
  return response.data;
}
