import { useCallback, useEffect, useState } from 'react';
import * as Linking from 'expo-linking';
import { supabase } from '../services/supabase';

/**
 * Password-recovery deep links (elvyn://reset-password#access_token=...&type=recovery).
 *
 * Listening starts once at module level, not inside a screen: while the app is
 * passcode-locked the navigator is unmounted, and a link that arrives then used
 * to be lost. The result waits in `pending` until the navigator is ready.
 */
export type RecoveryLink = { error?: string };

let pending: RecoveryLink | null = null;
let lastUrl: string | null = null;
let started = false;
const listeners = new Set<() => void>();

const EXPIRED = 'That reset link has expired or was already used. Request a new one.';

function publish(link: RecoveryLink) {
  pending = link;
  listeners.forEach((l) => l());
}

async function handleUrl(url: string | null) {
  if (!url || url === lastUrl) return;
  const hashIndex = url.indexOf('#');
  const queryIndex = url.indexOf('?');
  const raw = hashIndex >= 0 ? url.slice(hashIndex + 1) : queryIndex >= 0 ? url.slice(queryIndex + 1) : '';
  if (!raw || !url.includes('reset-password')) return;

  const params = new URLSearchParams(raw);
  const errorCode = params.get('error_code') ?? params.get('error');
  if (errorCode) {
    lastUrl = url;
    publish({ error: EXPIRED });
    return;
  }

  const access_token = params.get('access_token');
  const refresh_token = params.get('refresh_token');
  if (params.get('type') !== 'recovery' || !access_token || !refresh_token) return;

  lastUrl = url;
  try {
    const { error } = await supabase.auth.setSession({ access_token, refresh_token });
    publish(error ? { error: EXPIRED } : {});
  } catch {
    publish({ error: EXPIRED });
  }
}

function start() {
  if (started) return;
  started = true;
  Linking.getInitialURL().then(handleUrl).catch(() => {});
  Linking.addEventListener('url', (event) => { void handleUrl(event.url); });
}
start();

export function useAuthDeepLink() {
  const [link, setLink] = useState<RecoveryLink | null>(pending);

  useEffect(() => {
    const update = () => setLink(pending);
    listeners.add(update);
    update();
    return () => { listeners.delete(update); };
  }, []);

  const clear = useCallback(() => {
    pending = null;
    setLink(null);
  }, []);

  return { link, clear };
}
