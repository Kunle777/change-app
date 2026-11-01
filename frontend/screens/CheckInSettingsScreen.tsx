import { useEffect, useState } from 'react';
import { ActivityIndicator, Alert, Text, View } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { toggleCheckins } from '../services/settings';
import { getTodayCheckinStatus } from '../services/checkins';
import { RootStackParamList } from '../navigation/AppNavigator';
import { useColors } from '../theme/colors';
import ElvynMascot from '../components/ElvynMascot';
import SettingsPage from '../components/settings/SettingsPage';
import { SettingsGroup, SettingsRow } from '../components/settings/SettingsRow';

type Props = NativeStackScreenProps<RootStackParamList, 'CheckInSettings'>;

export default function CheckInSettingsScreen({ navigation }: Props) {
  const colors = useColors();
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getTodayCheckinStatus()
      .then((s) => setEnabled(s.checkins_enabled))
      .catch(() => setEnabled(true));
  }, []);

  async function handleToggle(next: boolean) {
    setEnabled(next);
    setSaving(true);
    try {
      await toggleCheckins(next);
    } catch {
      setEnabled(!next);
      Alert.alert("Couldn't update that", 'Check your connection and try again.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <SettingsPage title="Check-ins" onBack={() => navigation.goBack()}>
      {enabled === null ? (
        <ActivityIndicator style={{ marginTop: 40 }} color={colors.primary} />
      ) : (
        <>
          <SettingsGroup footer="Check-ins never affect your streak. Skip one and nothing is lost.">
            <SettingsRow
              icon="checkbox-outline"
              title="Daily check-ins"
              subtitle="Show morning and evening prompts on Home"
              switchValue={enabled}
              onSwitch={handleToggle}
              switchDisabled={saving}
              last
            />
          </SettingsGroup>

          <View
            style={{
              marginTop: 22, padding: 20, borderRadius: 16, alignItems: 'center',
              backgroundColor: colors.lavenderSurface, borderWidth: 1, borderColor: colors.border,
            }}
          >
            <ElvynMascot variant="supportive" size={84} />
            <Text style={{ color: colors.textMuted, textAlign: 'center', marginTop: 12, lineHeight: 20 }}>
              {enabled
                ? 'Elvyn will offer a quick check-in on Home each morning and evening.'
                : 'Check-in prompts and reminders are hidden. You can turn them back on any time.'}
            </Text>
          </View>
        </>
      )}
    </SettingsPage>
  );
}
