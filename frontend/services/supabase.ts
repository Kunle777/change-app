import { createClient } from '@supabase/supabase-js';
import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';

const ExpoSecureStoreAdapter = {
  getItem: (key: string) => SecureStore.getItemAsync(key),
  setItem: (key: string, value: string) => SecureStore.setItemAsync(key, value),
  removeItem: (key: string) => SecureStore.deleteItemAsync(key),
};

const LocalStorageAdapter = {
  getItem: async (key: string) => globalThis.localStorage?.getItem(key) ?? null,
  setItem: async (key: string, value: string) => globalThis.localStorage?.setItem(key, value),
  removeItem: async (key: string) => globalThis.localStorage?.removeItem(key),
};

export const supabase = createClient(
  'https://jcflmvahszgqikxtnuwn.supabase.co',
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpjZmxtdmFoc3pncWlreHRudXduIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODMyNzQzMDcsImV4cCI6MjA5ODg1MDMwN30.2Hch6dnANq1yzhYELZJG5qqO3_KI2tBgsje4GYQpPR8', // from Settings → API, the anon/public key, NOT service_role
  {
    auth: {
      storage: Platform.OS === 'web' ? LocalStorageAdapter : ExpoSecureStoreAdapter,
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: false,
    },
  },
);

let refreshPromise: ReturnType<typeof supabase.auth.refreshSession> | null = null;

export async function getAuthHeader(
  forceRefresh = false,
): Promise<{ Authorization: string; 'Content-Type': string }> {
  const { data, error } = await supabase.auth.getSession();
  let session = data.session;

  if (error) throw error;

  const expiresAt = session?.expires_at ?? 0;
  const isExpiringSoon = expiresAt <= Math.floor(Date.now() / 1000) + 60;

  if (session && (forceRefresh || isExpiringSoon)) {
    refreshPromise ??= supabase.auth.refreshSession();
    const pendingRefresh = refreshPromise;
    const refreshed = await pendingRefresh.finally(() => {
      if (refreshPromise === pendingRefresh) refreshPromise = null;
    });
    if (refreshed.error) {
      throw refreshed.error;
    }
    session = refreshed.data.session;
  }

  const token = session?.access_token;
  if (!token) throw new Error('No authenticated session available. Please log in again.');
  if (session?.expires_at && session.expires_at <= Math.floor(Date.now() / 1000)) {
    await supabase.auth.signOut();
    throw new Error('Authenticated session expired. Please log in again.');
  }

  return {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
}
