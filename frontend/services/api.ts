import axios from 'axios';
import Constants from 'expo-constants';
import { getAuthHeader, supabase } from './supabase';

function getApiBaseUrl() {
  const isWeb = typeof window !== 'undefined' && typeof window.location !== 'undefined';
  if (isWeb) {
    const { protocol, hostname } = window.location;
    return `${protocol}//${hostname}:8000`;
  }

  const expoConfig = (Constants as any).expoConfig;
  const legacyManifest = (Constants as any).manifest || (Constants as any).manifest2;
  const hostUri =
    expoConfig?.hostUri ||
    legacyManifest?.extra?.expoClient?.hostUri ||
    legacyManifest?.debuggerHost;
  const debuggerHost = typeof hostUri === 'string' ? hostUri.split(':')[0] : null;

  if (debuggerHost) {
    return `http://${debuggerHost}:8000`;
  }

  // Use the development machine LAN IP so a physical device can reach the backend
  return 'http://10.149.111.217:8000'; // Replace with your development machine's LAN IP address
}

const baseURL = getApiBaseUrl();
console.log('API base URL:', baseURL);

export const API_BASE_URL = baseURL;

export const api = axios.create({
  baseURL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
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
