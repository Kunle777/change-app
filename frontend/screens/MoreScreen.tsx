import { useCallback, useState } from 'react';
import { Alert, ScrollView, Text, TouchableOpacity, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFocusEffect } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { supabase } from '../services/supabase';
import { getMyProfile } from '../services/users';
import { useColors } from '../theme/colors';
import { SettingsGroup, SettingsRow } from '../components/settings/SettingsRow';
import { HAS_HELP } from '../config/support';
import { friendlyAuthError } from '../utils/authErrors';

export default function MoreScreen({ navigation }: any) {
  const colors = useColors();
  const [name, setName] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const [loggingOut, setLoggingOut] = useState(false);

  useFocusEffect(
    useCallback(() => {
      supabase.auth.getUser().then(({ data }) => setEmail(data.user?.email ?? null));
      getMyProfile().then((p) => setName(p.first_name ?? null)).catch(() => {});
    }, []),
  );

  function handleLogout() {
    Alert.alert('Log out', 'Are you sure you want to log out?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Log out',
        style: 'destructive',
        onPress: async () => {
          if (loggingOut) return;
          setLoggingOut(true);
          const { error } = await supabase.auth.signOut();
          setLoggingOut(false);
          if (error) {
            Alert.alert('Could not log out', friendlyAuthError(error));
            return;
          }
          navigation.getParent()?.reset({ index: 0, routes: [{ name: 'Login' }] });
        },
      },
    ]);
  }

  const initial = (name ?? email ?? '?').trim().charAt(0).toUpperCase();

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.background }}>
      <ScrollView contentContainerStyle={{ paddingHorizontal: 20, paddingBottom: 32 }}>
        <Text style={{ color: colors.text, fontSize: 26, fontWeight: '800', marginTop: 8 }}>More</Text>

        <TouchableOpacity
          onPress={() => navigation.navigate('Profile')}
          accessibilityRole="button"
          activeOpacity={0.8}
          style={{
            flexDirection: 'row', alignItems: 'center', marginTop: 18, padding: 14, borderRadius: 16,
            backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border,
          }}
        >
          <View
            style={{
              width: 48, height: 48, borderRadius: 24, backgroundColor: colors.primary,
              alignItems: 'center', justifyContent: 'center', marginRight: 14,
            }}
          >
            <Text style={{ color: '#fff', fontSize: 20, fontWeight: '800' }}>{initial}</Text>
          </View>
          <View style={{ flex: 1 }}>
            <Text style={{ color: colors.text, fontSize: 17, fontWeight: '700' }}>{name ?? 'Your profile'}</Text>
            <Text style={{ color: colors.textMuted, fontSize: 13, marginTop: 2 }} numberOfLines={1}>
              {email ?? 'View your account'}
            </Text>
          </View>
          <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
        </TouchableOpacity>

        <SettingsGroup label="Preferences">
          <SettingsRow icon="notifications-outline" title="Notifications" subtitle="Reminders and system alerts" onPress={() => navigation.navigate('NotificationSettings')} />
          <SettingsRow icon="contrast-outline" title="Appearance" subtitle="Light, dark or system" onPress={() => navigation.navigate('Appearance')} />
          <SettingsRow icon="checkbox-outline" title="Check-ins" subtitle="Morning and evening prompts" onPress={() => navigation.navigate('CheckInSettings')} />
          <SettingsRow icon="shield-checkmark-outline" title="Security & Privacy" subtitle="Password and your data" onPress={() => navigation.navigate('SecurityPrivacy')} last />
        </SettingsGroup>

        <SettingsGroup label="Elvyn">
          {HAS_HELP ? (
            <SettingsRow icon="help-circle-outline" title="Help & Support" subtitle="Get in touch or read our policies" onPress={() => navigation.navigate('HelpSupport')} />
          ) : null}
          <SettingsRow icon="information-circle-outline" title="About Elvyn" onPress={() => navigation.navigate('About')} last />
        </SettingsGroup>

        <SettingsGroup label="Account">
          <SettingsRow icon="log-out-outline" title={loggingOut ? 'Logging out…' : 'Log out'} onPress={handleLogout} danger last />
        </SettingsGroup>
      </ScrollView>
    </SafeAreaView>
  );
}
