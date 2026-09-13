import * as WebBrowser from 'expo-web-browser';
import * as AuthSession from 'expo-auth-session';
import { supabase } from './supabase';

WebBrowser.maybeCompleteAuthSession();

export async function signInWithGoogle() {
  const redirectTo = AuthSession.makeRedirectUri({
    scheme: 'elvyn',
    path: 'auth/callback',
  });

  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo,
      skipBrowserRedirect: true,
    },
  });

  if (error || !data?.url) {
    throw new Error(error?.message ?? 'Could not start Google sign-in');
  }

  const result = await WebBrowser.openAuthSessionAsync(data.url, redirectTo);

  if (result.type !== 'success' || !result.url) {
    throw new Error('Google sign-in was cancelled');
  }

  return await finishGoogleSignIn(result.url);
}

async function finishGoogleSignIn(callbackUrl: string) {
  const [urlWithoutFragment, fragment] = callbackUrl.split('#');
  const query = urlWithoutFragment.split('?')[1] ?? '';
  const params = new URLSearchParams(fragment || query);
  const callbackError = params.get('error_description') || params.get('error');
  if (callbackError) {
    throw new Error(decodeURIComponent(callbackError.replace(/\+/g, ' ')));
  }
  const access_token = params.get('access_token');
  const refresh_token = params.get('refresh_token');

  if (access_token && refresh_token) {
    const { data, error } = await supabase.auth.setSession({
      access_token,
      refresh_token,
    });

    if (error) {
      throw new Error(error.message);
    }

    return data.session;
  }

  const code = new URLSearchParams(query).get('code');
  if (!code) {
    throw new Error('No session data returned from Google sign-in');
  }

  const { data, error } = await supabase.auth.exchangeCodeForSession(code);
  if (error) {
    throw new Error(error.message);
  }

  return data.session;
}
