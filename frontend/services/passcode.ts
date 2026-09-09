// services/passcode.ts
import * as SecureStore from 'expo-secure-store';
import * as Crypto from 'expo-crypto';

const PASSCODE_KEY = 'app_passcode_hash';

async function hashPasscode(passcode: string): Promise<string> {
  return Crypto.digestStringAsync(Crypto.CryptoDigestAlgorithm.SHA256, passcode);
}

export async function setPasscode(passcode: string): Promise<void> {
  const hash = await hashPasscode(passcode);
  await SecureStore.setItemAsync(PASSCODE_KEY, hash);
}

export async function hasPasscode(): Promise<boolean> {
  const stored = await SecureStore.getItemAsync(PASSCODE_KEY);
  return stored !== null;
}

export async function verifyPasscode(passcode: string): Promise<boolean> {
  const stored = await SecureStore.getItemAsync(PASSCODE_KEY);
  if (!stored) return false;
  const hash = await hashPasscode(passcode);
  return hash === stored;
}

export async function clearPasscode(): Promise<void> {
  await SecureStore.deleteItemAsync(PASSCODE_KEY);
}