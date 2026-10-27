import { useCallback, useState } from 'react';
import { Alert, Text, View } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { hasPasscode } from '../services/passcode';
import { RootStackParamList } from '../navigation/AppNavigator';
import { useColors } from '../theme/colors';
import SettingsPage from '../components/settings/SettingsPage';
import { SettingsGroup, SettingsRow } from '../components/settings/SettingsRow';

type Props = NativeStackScreenProps<RootStackParamList, 'SecurityPrivacy'>;

export default function SecurityPrivacyScreen({ navigation }: Props) {
  const colors = useColors();
  const [passcodeOn, setPasscodeOn] = useState<boolean | null>(null);

  useFocusEffect(
    useCallback(() => {
      hasPasscode().then(setPasscodeOn);
    }, []),
  );

  function handlePasscode() {
    if (!passcodeOn) {
      navigation.navigate('PasscodeSetup', { mode: 'create' });
      return;
    }
    Alert.alert('App passcode', 'What would you like to do?', [
      { text: 'Change passcode', onPress: () => navigation.navigate('PasscodeSetup', { mode: 'change' }) },
      { text: 'Turn off', style: 'destructive', onPress: () => navigation.navigate('PasscodeSetup', { mode: 'disable' }) },
      { text: 'Cancel', style: 'cancel' },
    ]);
  }

  return (
    <SettingsPage title="Security & Privacy" onBack={() => navigation.goBack()}>
      <SettingsGroup
        label="Security"
        footer="The passcode locks Elvyn on this phone whenever you come back to the app. It is separate from your account password."
      >
        <SettingsRow
          icon="keypad-outline"
          title="App passcode"
          subtitle="Keep Elvyn private on this phone"
          value={passcodeOn === null ? '' : passcodeOn ? 'On' : 'Off'}
          onPress={handlePasscode}
        />
        <SettingsRow icon="key-outline" title="Change password" subtitle="Update your account password" onPress={() => navigation.navigate('ChangePassword')} last />
      </SettingsGroup>

      <View
        style={{
          marginTop: 22, padding: 16, borderRadius: 16, backgroundColor: colors.lavenderSurface,
          borderWidth: 1, borderColor: colors.border,
        }}
      >
        <Text style={{ color: colors.text, fontWeight: '700', marginBottom: 6 }}>Your data</Text>
        <Text style={{ color: colors.textMuted, lineHeight: 20 }}>
          Your tasks, Brain Dumps and check-ins belong to your account and are visible only to you. AI replies
          are built from the parts of your data needed to answer your question. Searchable AI memory is off by
          default and is only used if you opt in.
        </Text>
      </View>
    </SettingsPage>
  );
}
