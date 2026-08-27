import { useEffect, useState } from 'react';
import * as Linking from 'expo-linking';
import { supabase } from '../services/supabase';

export function useAuthDeepLink() {
  const [showResetPassword, setShowResetPassword] = useState(false);

  useEffect(() => {
    async function handleUrl(url: string | null) {
      if (!url) return;
      const fragment = url.split('#')[1];
      if (!fragment) return;

      const params = new URLSearchParams(fragment);
      const access_token = params.get('access_token');
      const refresh_token = params.get('refresh_token');
      const type = params.get('type');

      if (type === 'recovery' && access_token && refresh_token) {
        await supabase.auth.setSession({ access_token, refresh_token });
        setShowResetPassword(true);
      }
    }

    Linking.getInitialURL().then(handleUrl);

    const subscription = Linking.addEventListener('url', (event) => handleUrl(event.url));
    return () => subscription.remove();
  }, []);

  return { showResetPassword, setShowResetPassword };
}
