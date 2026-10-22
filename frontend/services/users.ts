import { getAuthHeader } from './supabase';
import { API_BASE_URL } from './api';

export async function updateCountry(countryCode: string) {
  const res = await fetch(`${API_BASE_URL}/api/users/country`, {
    method: 'PATCH',
    headers: await getAuthHeader(),
    body: JSON.stringify({ country_code: countryCode }),
  });
  if (!res.ok) throw new Error('Failed to update country');
  return res.json();
}

export async function getEntitlements() {
  const res = await fetch(`${API_BASE_URL}/api/users/entitlements`, {
    headers: await getAuthHeader(),
  });
  if (!res.ok) throw new Error('Failed to fetch entitlements');
  return res.json();
}

export async function getMyProfile() {
  const res = await fetch(`${API_BASE_URL}/api/users/me`, {
    headers: await getAuthHeader(),
  });
  if (!res.ok) throw new Error('Failed to fetch profile');
  return res.json();
}
