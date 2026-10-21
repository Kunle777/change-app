export function friendlyAuthError(err: unknown): string {
  const e = err as { message?: string; code?: string; name?: string } | null;
  console.log('[auth]', err); 
  const msg = e?.message ?? '';

  if (e?.name === 'AuthRetryableFetchError' || /network request failed|failed to fetch/i.test(msg))
    return "Can't connect. Check your internet and try again.";

  switch (e?.code) {
    case 'invalid_credentials': return 'Email or password is incorrect.';
    case 'email_not_confirmed': return 'Please confirm your email first. Check your inbox.';
    case 'over_request_rate_limit':
    case 'over_email_send_rate_limit': return 'Too many attempts. Try again in a few minutes.';
    case 'user_already_exists': return 'An account with this email already exists. Try logging in.';
    case 'weak_password': return 'Choose a stronger password (at least 8 characters).';
  }
  if (/invalid login credentials/i.test(msg)) return 'Email or password is incorrect.';
  return 'Something went wrong. Please try again.';
}

export const isValidEmail = (v: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim());
export const MIN_PASSWORD = 8;