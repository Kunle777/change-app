import { getAuthHeader } from './supabase'; // reuse your existing pattern from tasks.ts
import { API_BASE_URL } from './api';

async function request(path: string, method: string, body?: object) {
  const headers = await getAuthHeader();
  const res = await fetch(`${API_BASE_URL}/api/savings${path}`, {
    method,
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Request failed');
  return data;
}

export const setupBankAccount = (payload: {
  first_name: string; last_name: string; bvn: string;
  bank_code: string; account_number: string;
}) => request('/bank-account/setup', 'POST', payload);

export const createVault = (payload: {
  name: string; target_amount: number; lock_until: string;
}) => request('', 'POST', payload);

export const listVaults = () => request('', 'GET');

export const createDepositIntent = (vaultId: string, amount: number) =>
  request(`/${vaultId}/deposit-intent`, 'POST', { amount });

export const setupWithdrawalPin = (pin: string) =>
  request('/withdrawal-pin/setup', 'POST', { pin });

export const requestWithdrawal = (vaultId: string, amount: number, withdrawal_pin: string) =>
  request(`/${vaultId}/withdraw`, 'POST', { amount, withdrawal_pin });