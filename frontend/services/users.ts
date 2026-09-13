import { supabase } from './supabase';
import { API_BASE_URL } from './api';

async function authHeader() {
  const { data } = await supabase.auth.getSession();
  return { Authorization: `Bearer ${data.session?.access_token}` };
}

export async function updateCountry(countryCode: string) {
  const res = await fetch(`${API_BASE_URL}/api/users/country`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      ...(await authHeader()),
    },
    body: JSON.stringify({ country_code: countryCode }),
  });
  if (!res.ok) throw new Error('Failed to update country');
  return res.json();
}

export async function getEntitlements() {
  const res = await fetch(`${API_BASE_URL}/api/users/entitlements`, {
    headers: await authHeader(),
  });
  if (!res.ok) throw new Error('Failed to fetch entitlements');
  return res.json();
}
