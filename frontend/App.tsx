import AppNavigator from "./navigation/AppNavigator";
import { NavigationContainer, useNavigation } from "@react-navigation/native";
import { KeyboardProvider } from "react-native-keyboard-controller";
import { useAuthDeepLink } from "./hooks/useAuthDeepLink";
import { AppState, AppStateStatus } from 'react-native';
import { useState, useRef, useEffect } from 'react';
import { hasPasscode } from './services/passcode';
import PasscodeLockScreen from './screens/PasscodeLockScreen'

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

export default function App() {
  const [locked, setLocked] = useState(true);
  const appState = useRef<AppStateStatus>(AppState.currentState);

  useEffect(() => {
    hasPasscode().then((exists) => setLocked(exists));

    const subscription = AppState.addEventListener('change', (nextState) => {
      if (appState.current.match(/inactive|background/) && nextState === 'active') {
        hasPasscode().then((exists) => {
          if (exists) setLocked(true);
        });
      }
      appState.current = nextState;
    });

    return () => subscription.remove();
  }, []);

  if (locked) {
    return <PasscodeLockScreen onUnlock={() => setLocked(false)} />;
  }

  return (
    <KeyboardProvider>
      <NavigationContainer>
        <AppNavigator />
        <DeepLinkHandler />
      </NavigationContainer>
    </KeyboardProvider>
  );
}
