import axios from 'axios';
import { getAuthHeader, supabase } from './supabase';

const baseURL = process.env.EXPO_PUBLIC_API_URL?.trim() ?? '';

if (!baseURL && __DEV__) {
  console.warn(
    'EXPO_PUBLIC_API_URL is not set. Add it to frontend/.env so the app can reach your API.',
  );
}

export const API_BASE_URL = baseURL;

export const api = axios.create({
  baseURL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  if (!baseURL) {
    throw new Error('API request blocked: set EXPO_PUBLIC_API_URL in frontend/.env.');
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config as (typeof error.config & { _authRetry?: boolean }) | undefined;
    if (error.response?.status !== 401 || !config || config._authRetry) throw error;

    config._authRetry = true;
    config.headers = await getAuthHeader(true);
    try {
      return await api.request(config);
    } catch (retryError: any) {
      if (retryError.response?.status === 401) {
        await supabase.auth.signOut();
      }
      throw retryError;
    }
  },
);
