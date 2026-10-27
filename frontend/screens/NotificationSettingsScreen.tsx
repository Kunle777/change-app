import { useCallback, useState } from 'react';
import { Alert, Linking } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import * as Notifications from 'expo-notifications';
import { RootStackParamList } from '../navigation/AppNavigator';
import { scheduleTestNotification } from '../services/notifications';
import { getDefaultPriorityReminder, setDefaultPriorityReminder } from '../services/preferences';
import SettingsPage from '../components/settings/SettingsPage';
import { SettingsGroup, SettingsRow } from '../components/settings/SettingsRow';

type Props = NativeStackScreenProps<RootStackParamList, 'NotificationSettings'>;

export default function NotificationSettingsScreen({ navigation }: Props) {
  const [allowed, setAllowed] = useState<boolean | null>(null);
  const [defaultPriority, setDefaultPriority] = useState(false);
  const [testing, setTesting] = useState(false);

  // Re-check on focus: the person may have just changed it in system settings.
  useFocusEffect(
    useCallback(() => {
      Notifications.getPermissionsAsync()
        .then((p) => setAllowed(p.granted))
        .catch(() => setAllowed(null));
      getDefaultPriorityReminder().then(setDefaultPriority);
    }, []),
  );

  function toggleDefaultPriority(next: boolean) {
    setDefaultPriority(next);
    setDefaultPriorityReminder(next).catch(() => setDefaultPriority(!next));
  }

  async function handleTest() {
    setTesting(true);
    try {
      await scheduleTestNotification();
      Alert.alert('Test scheduled', 'Lock your phone and wait about 8 seconds.');
    } catch {
      Alert.alert(
        "Couldn't send a test",
        'Test alerts only work in the installed Android app, with notifications allowed.',
      );
    } finally {
      setTesting(false);
    }
  }

  return (
    <SettingsPage title="Notifications" onBack={() => navigation.goBack()}>
      <SettingsGroup
        label="Task reminders"
        footer="Priority reminders use a louder Android channel so important tasks are harder to miss, when your phone allows it. You can still set this per task."
      >
        <SettingsRow
          icon="flash-outline"
          title="Priority reminders by default"
          subtitle="Turn on priority for every new task"
          switchValue={defaultPriority}
          onSwitch={toggleDefaultPriority}
          last
        />
      </SettingsGroup>

      <SettingsGroup
        label="On this phone"
        footer={allowed === false ? 'Reminders can’t reach you while notifications are off for Elvyn.' : undefined}
      >
        <SettingsRow
          icon="notifications-outline"
          title="Allow notifications"
          subtitle="Manage in your device settings"
          value={allowed === null ? '' : allowed ? 'On' : 'Off'}
          onPress={() => Linking.openSettings()}
        />
        <SettingsRow
          icon="paper-plane-outline"
          title="Send a test notification"
          subtitle="Arrives in about 8 seconds"
          onPress={handleTest}
          loading={testing}
          last
        />
      </SettingsGroup>
    </SettingsPage>
  );
}
