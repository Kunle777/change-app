import axios from 'axios';
import Constants from 'expo-constants';

function getApiBaseUrl() {
  const isWeb = typeof window !== 'undefined' && typeof window.location !== 'undefined';
  if (isWeb) {
    const { protocol, hostname } = window.location;
    return `${protocol}//${hostname}:8000`;
  }

  const manifest = (Constants as any).manifest || (Constants as any).manifest2;
  const debuggerHost =
    manifest && typeof manifest.debuggerHost === 'string'
      ? manifest.debuggerHost.split(':')[0]
      : null;

  if (debuggerHost) {
    return `http://${debuggerHost}:8000`;
  }

  // Use the development machine LAN IP so a physical device can reach the backend
  return 'http://10.150.124.217:8000';
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
