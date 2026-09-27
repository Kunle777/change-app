import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  Switch,
  StyleSheet,
  Alert,
  ActivityIndicator,
  TouchableOpacity,
  ScrollView,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { toggleCheckins } from '../services/settings';
import { getTodayCheckinStatus } from '../services/checkins';

const STORAGE_KEYS = {
  NOTIFICATIONS_ENABLED: 'settings_notifications_enabled',
  DEFAULT_PRIORITY: 'settings_default_priority',
};

export default function SettingsScreen() {
  const navigation = useNavigation<any>();
  const [checkinsEnabled, setCheckinsEnabled] = useState<boolean | null>(null);
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [defaultPriority, setDefaultPriority] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    // Load check-in status from API
    getTodayCheckinStatus()
      .then((data) => setCheckinsEnabled(data.checkins_enabled))
      .catch(() => setCheckinsEnabled(true));

    // Load saved notification preferences from AsyncStorage
    loadLocalSettings();
  }, []);

  const loadLocalSettings = async () => {
    try {
      const savedNotifs = await AsyncStorage.getItem(STORAGE_KEYS.NOTIFICATIONS_ENABLED);
      const savedPriority = await AsyncStorage.getItem(STORAGE_KEYS.DEFAULT_PRIORITY);

      if (savedNotifs !== null) setNotificationsEnabled(JSON.parse(savedNotifs));
      if (savedPriority !== null) setDefaultPriority(JSON.parse(savedPriority));
    } catch {
      // Fallback to default values on error
    }
  };

  const handleToggleCheckins = async (value: boolean) => {
    setCheckinsEnabled(value);
    setSaving(true);
    try {
      await toggleCheckins(value);
    } catch (err: any) {
      setCheckinsEnabled(!value);
      Alert.alert('Error', err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleToggleNotifications = async (value: boolean) => {
    setNotificationsEnabled(value);
    await AsyncStorage.setItem(STORAGE_KEYS.NOTIFICATIONS_ENABLED, JSON.stringify(value));
  };

  const handleToggleDefaultPriority = async (value: boolean) => {
    setDefaultPriority(value);
    await AsyncStorage.setItem(STORAGE_KEYS.DEFAULT_PRIORITY, JSON.stringify(value));
  };

  if (checkinsEnabled === null) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#4F46E5" />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      {/* General Settings Section */}
      <Text style={styles.sectionTitle}>General</Text>

      <View style={styles.row}>
        <View style={styles.textContainer}>
          <Text style={styles.label}>Daily check-ins</Text>
          <Text style={styles.sublabel}>Show morning and evening check-in prompts on Home</Text>
        </View>
        <Switch
          value={checkinsEnabled}
          onValueChange={handleToggleCheckins}
          disabled={saving}
          trackColor={{ false: '#d1d5db', true: '#4F46E5' }}
        />
      </View>

      <TouchableOpacity style={styles.row} onPress={() => navigation.navigate('ChangePassword')}>
        <Text style={styles.label}>Change Password</Text>
      </TouchableOpacity>

      {/* Notifications Section */}
      <Text style={[styles.sectionTitle, { marginTop: 28 }]}>Notifications</Text>

      <View style={styles.row}>
        <View style={styles.textContainer}>
          <Text style={styles.label}>Enable Push Notifications</Text>
          <Text style={styles.sublabel}>Allow task and check-in reminders on this device</Text>
        </View>
        <Switch
          value={notificationsEnabled}
          onValueChange={handleToggleNotifications}
          trackColor={{ false: '#d1d5db', true: '#4F46E5' }}
        />
      </View>

      <View style={styles.row}>
        <View style={styles.textContainer}>
          <Text style={styles.label}>Default Priority Reminders 🚨</Text>
          <Text style={styles.sublabel}>
            Automatically enable Priority Reminder mode when creating new tasks
          </Text>
        </View>
        <Switch
          value={defaultPriority}
          onValueChange={handleToggleDefaultPriority}
          disabled={!notificationsEnabled}
          trackColor={{ false: '#d1d5db', true: '#4F46E5' }}
        />
      </View>

      {/* Explanatory Info Card */}
      <View style={styles.infoCard}>
        <Text style={styles.infoTitle}>Reminder Types Explained</Text>

        <View style={{ marginBottom: 10 }}>
          <Text style={styles.infoLabel}>Standard Reminders</Text>
          <Text style={styles.infoSublabel}>
            Regular alerts sent for scheduled tasks and check-ins. Respects Do Not Disturb mode.
          </Text>
        </View>

        <View>
          <Text style={styles.infoLabel}>Priority Reminders</Text>
          <Text style={styles.infoSublabel}>
            Uses high-importance channels to trigger pop-ups and bypass silent settings when
            supported by your phone. Set per-task in Create/Edit Task.
          </Text>
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  container: { flex: 1, padding: 20, backgroundColor: '#fff' },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: '#111', marginBottom: 6 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderColor: '#eee',
  },
  textContainer: { flex: 1, paddingRight: 10 },
  label: { fontSize: 15, fontWeight: '600', color: '#111' },
  sublabel: { fontSize: 12, color: '#888', marginTop: 2 },
  infoCard: {
    marginTop: 24,
    marginBottom: 40,
    backgroundColor: '#F9FAFB',
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  infoTitle: { fontSize: 13, fontWeight: '700', color: '#374151', marginBottom: 12 },
  infoLabel: { fontSize: 13, fontWeight: '600', color: '#111' },
  infoSublabel: { fontSize: 12, color: '#6B7280', marginTop: 2 },
});
