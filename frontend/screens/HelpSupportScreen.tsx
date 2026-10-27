import { Alert, Linking } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/AppNavigator';
import { PRIVACY_POLICY_URL, SUPPORT_EMAIL, TERMS_URL } from '../config/support';
import SettingsPage from '../components/settings/SettingsPage';
import { SettingsGroup, SettingsRow } from '../components/settings/SettingsRow';

type Props = NativeStackScreenProps<RootStackParamList, 'HelpSupport'>;

async function open(url: string) {
  try {
    await Linking.openURL(url);
  } catch {
    Alert.alert("Couldn't open that", 'Please try again in a moment.');
  }
}

export default function HelpSupportScreen({ navigation }: Props) {
  return (
    <SettingsPage title="Help & Support" onBack={() => navigation.goBack()}>
      {SUPPORT_EMAIL ? (
        <SettingsGroup label="Get help">
          <SettingsRow
            icon="mail-outline"
            title="Contact support"
            subtitle={SUPPORT_EMAIL}
            onPress={() => open(`mailto:${SUPPORT_EMAIL}?subject=${encodeURIComponent('Elvyn support')}`)}
            last
          />
        </SettingsGroup>
      ) : null}
      {PRIVACY_POLICY_URL || TERMS_URL ? (
        <SettingsGroup label="Policies">
          {PRIVACY_POLICY_URL ? (
            <SettingsRow icon="document-text-outline" title="Privacy policy" onPress={() => open(PRIVACY_POLICY_URL)} last={!TERMS_URL} />
          ) : null}
          {TERMS_URL ? (
            <SettingsRow icon="reader-outline" title="Terms of service" onPress={() => open(TERMS_URL)} last />
          ) : null}
        </SettingsGroup>
      ) : null}
    </SettingsPage>
  );
}
