import { createClient } from '@supabase/supabase-js';
import * as SecureStore from 'expo-secure-store';

const ExpoSecureStoreAdapter = {
  getItem: (key: string) => SecureStore.getItemAsync(key),
  setItem: (key: string, value: string) => SecureStore.setItemAsync(key, value),
  removeItem: (key: string) => SecureStore.deleteItemAsync(key),
};

export const supabase = createClient(
  'https://jcflmvahszgqikxtnuwn.supabase.co',
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpjZmxtdmFoc3pncWlreHRudXduIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODMyNzQzMDcsImV4cCI6MjA5ODg1MDMwN30.2Hch6dnANq1yzhYELZJG5qqO3_KI2tBgsje4GYQpPR8', // from Settings → API, the anon/public key, NOT service_role
  {
    auth: {
      storage: ExpoSecureStoreAdapter,
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: false,
    },
  },
);
