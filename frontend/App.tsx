import AppNavigator from "./navigation/AppNavigator";
import { DarkTheme, DefaultTheme, NavigationContainer, useNavigation } from "@react-navigation/native";
import { useAuthDeepLink } from "./hooks/useAuthDeepLink";
import { AppState, AppStateStatus } from 'react-native';
import { useState, useRef, useEffect } from 'react';
import { hasPasscode } from './services/passcode';
import PasscodeLockScreen from './screens/PasscodeLockScreen';
import { ThemeProvider, useTheme } from './contexts/ThemeContext';
import { useColors } from './theme/colors';
import { supabase } from './services/supabase';
import { clearTaskReminders, reconcileNotifications } from './services/notifications';
import * as Notifications from 'expo-notifications';
import { recordTaskEvent } from './services/taskEvents';
import { recordDailyActivity } from './services/activity';

function DeepLinkHandler() {
  const navigation = useNavigation<any>();
  const { showResetPassword, setShowResetPassword } = useAuthDeepLink();

  useEffect(() => {
    if (showResetPassword) {
      navigation.navigate('ResetPassword');
      setShowResetPassword(false);
    }
  }, [showResetPassword]);

  return null;
}

function AppContent() {
  const [locked, setLocked] = useState(true);
  const appState = useRef<AppStateStatus>(AppState.currentState);
  const { resolvedTheme } = useTheme();
  const colors = useColors();

  useEffect(() => {
    const handledResponseIds = new Set<string>();
    const recordOpenedReminder = (response: Notifications.NotificationResponse) => {
      const request = response.notification.request;
      const data = request.content.data;
      if (
        response.actionIdentifier !== Notifications.DEFAULT_ACTION_IDENTIFIER ||
        data?.type !== 'task_reminder' ||
        typeof data.taskId !== 'string' ||
        handledResponseIds.has(request.identifier)
      ) return;

      handledResponseIds.add(request.identifier);
      void recordTaskEvent(data.taskId, 'reminder_opened', undefined, request.identifier);
    };

    const subscription = Notifications.addNotificationResponseReceivedListener(recordOpenedReminder);
    void Notifications.getLastNotificationResponseAsync()
      .then(async (response) => {
        if (response) recordOpenedReminder(response);
        await Notifications.clearLastNotificationResponseAsync();
      })
      .catch((error) => console.warn('Could not read the last notification response', error));

    return () => subscription.remove();
  }, []);

  useEffect(() => {
    hasPasscode().then((exists) => setLocked(exists));

    const reconcileIfAuthenticated = async () => {
      const { data, error } = await supabase.auth.getSession();
      if (!error && data.session) {
        await reconcileNotifications();
        void recordDailyActivity().catch((activityError) =>
          console.warn('Could not record daily activity', activityError),
        );
      }
    };

    void reconcileIfAuthenticated();
    const { data: authListener } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'SIGNED_IN' && session) {
        // Supabase recommends deferring other auth calls until its callback returns.
        setTimeout(() => void reconcileIfAuthenticated(), 0);
      } else if (event === 'SIGNED_OUT') {
        setTimeout(() => void clearTaskReminders(), 0);
      }
    });

    const subscription = AppState.addEventListener('change', (nextState) => {
      if (appState.current.match(/inactive|background/) && nextState === 'active') {
        hasPasscode().then((exists) => {
          if (exists) setLocked(true);
        });
        void reconcileIfAuthenticated();
      }
      appState.current = nextState;
    });

    return () => {
      subscription.remove();
      authListener.subscription.unsubscribe();
    };
  }, []);

  if (locked) {
    return <PasscodeLockScreen onUnlock={() => setLocked(false)} />;
  }

  const navigationTheme = resolvedTheme === 'dark' ? DarkTheme : DefaultTheme;
  const themedNavigation = {
    ...navigationTheme,
    dark: resolvedTheme === 'dark',
    colors: {
      ...navigationTheme.colors,
      primary: colors.primary,
      background: colors.background,
      card: colors.surface,
      text: colors.text,
      border: colors.border,
      notification: colors.accent,
    },
  };

  return (
    <NavigationContainer theme={themedNavigation}>
      <AppNavigator />
      <DeepLinkHandler />
    </NavigationContainer>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
}
