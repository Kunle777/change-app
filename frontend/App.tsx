import React, { useEffect } from "react";
import AppNavigator from "./navigation/AppNavigator";
import { NavigationContainer, useNavigation } from "@react-navigation/native";
import { KeyboardProvider } from "react-native-keyboard-controller";
import { useAuthDeepLink } from "./hooks/useAuthDeepLink";

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
  return (
    <KeyboardProvider>
      <NavigationContainer>
        <AppNavigator />
        <DeepLinkHandler />
      </NavigationContainer>
    </KeyboardProvider>
  );
}
