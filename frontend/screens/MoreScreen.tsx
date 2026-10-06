import { useState } from 'react';
import { Alert, ScrollView, Text, TouchableOpacity } from 'react-native';
import { supabase } from '../services/supabase';
import { useColors } from '../theme/colors';

const MENU_ITEMS = [
  { label: 'Profile', route: null },
  { label: 'Notifications', route: null },
  { label: 'Appearance', route: 'Appearance' },
  { label: 'Check-ins', route: null },
  { label: 'Security & Privacy', route: null },
  { label: 'AI & Personalization', route: null },
  { label: 'Help & Support', route: null },
  { label: 'About', route: null },
] as const;

export default function MoreScreen({ navigation }: any) {
  const colors = useColors();
  const [loggingOut, setLoggingOut] = useState(false);

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
            Alert.alert('Could not log out', error.message);
            return;
          }
          navigation.getParent()?.reset({ index: 0, routes: [{ name: 'Login' }] });
        },
      },
    ]);
  }

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.background }}
      contentContainerStyle={{ padding: 20, paddingTop: 50, paddingBottom: 32 }}
    >
      <Text style={{ fontSize: 20, fontWeight: '700', color: colors.text, marginBottom: 20 }}>
        More
      </Text>

      {MENU_ITEMS.map((item) => {
        const enabled = item.route !== null;
        return (
          <TouchableOpacity
            key={item.label}
            disabled={!enabled}
            onPress={() => enabled && navigation.navigate(item.route)}
            accessibilityRole="button"
            accessibilityState={{ disabled: !enabled }}
            style={{
              flexDirection: 'row',
              justifyContent: 'space-between',
              alignItems: 'center',
              paddingVertical: 14,
              borderBottomWidth: 1,
              borderBottomColor: colors.border,
              opacity: enabled ? 1 : 0.55,
            }}
          >
            <Text style={{ color: colors.text, fontSize: 15 }}>{item.label}</Text>
            {!enabled && <Text style={{ color: colors.textMuted, fontSize: 11 }}>Coming soon</Text>}
          </TouchableOpacity>
        );
      })}

      <TouchableOpacity
        onPress={() => navigation.navigate('Settings')}
        accessibilityRole="button"
        style={{
          flexDirection: 'row',
          justifyContent: 'space-between',
          alignItems: 'center',
          paddingVertical: 14,
          borderBottomWidth: 1,
          borderBottomColor: colors.border,
        }}
      >
        <Text style={{ color: colors.text, fontSize: 15 }}>Existing settings</Text>
        <Text style={{ color: colors.textMuted, fontSize: 11 }}>Check-ins and password</Text>
      </TouchableOpacity>

      <TouchableOpacity
        onPress={handleLogout}
        disabled={loggingOut}
        accessibilityRole="button"
        style={{ marginTop: 30, paddingVertical: 12 }}
      >
        <Text style={{ color: colors.danger, fontWeight: '600', textAlign: 'center' }}>
          {loggingOut ? 'Logging out…' : 'Log out'}
        </Text>
      </TouchableOpacity>
    </ScrollView>
  );
}
