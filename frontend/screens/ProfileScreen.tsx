import { useEffect, useState } from 'react';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { supabase } from '../services/supabase';
import { getMyProfile } from '../services/users';
import { RootStackParamList } from '../navigation/AppNavigator';
import SettingsPage from '../components/settings/SettingsPage';
import { SettingsGroup, SettingsRow } from '../components/settings/SettingsRow';

type Props = NativeStackScreenProps<RootStackParamList, 'Profile'>;

export default function ProfileScreen({ navigation }: Props) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'Africa/Lagos';

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => setEmail(data.user?.email ?? ''));
    getMyProfile().then((p) => setName(p.first_name ?? '')).catch(() => {});
  }, []);

  return (
    <SettingsPage title="Profile" onBack={() => navigation.goBack()}>
      <SettingsGroup label="Personal information">
        <SettingsRow icon="person-outline" title="Name" subtitle={name || 'Not set'} />
        <SettingsRow icon="mail-outline" title="Email" subtitle={email || '—'} />
        <SettingsRow icon="time-outline" title="Time zone" subtitle={`${timezone} (from your phone)`} last />
      </SettingsGroup>

      <SettingsGroup label="Account">
        <SettingsRow icon="lock-closed-outline" title="Change password" onPress={() => navigation.navigate('ChangePassword')} last />
      </SettingsGroup>
    </SettingsPage>
  );
}
