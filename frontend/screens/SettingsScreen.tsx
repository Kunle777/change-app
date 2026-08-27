import React, { useEffect, useState } from 'react';
import { View, Text, Switch, StyleSheet, Alert, ActivityIndicator, TouchableOpacity } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { toggleCheckins } from '../services/settings';
import { getTodayCheckinStatus } from '../services/checkins';

export default function SettingsScreen() {
  const navigation = useNavigation<any>();
  const [checkinsEnabled, setCheckinsEnabled] = useState<boolean | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getTodayCheckinStatus()
      .then((data) => setCheckinsEnabled(data.checkins_enabled))
      .catch(() => setCheckinsEnabled(true));
  }, []);

  const handleToggle = async (value: boolean) => {
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

  if (checkinsEnabled === null) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.row}>
        <View style={{ flex: 1 }}>
          <Text style={styles.label}>Daily check-ins</Text>
          <Text style={styles.sublabel}>Show morning and evening check-in prompts on Home</Text>
        </View>
        <Switch value={checkinsEnabled} onValueChange={handleToggle} disabled={saving} />
      </View>
      <TouchableOpacity style={styles.row} onPress={() => navigation.navigate('ChangePassword')}>
        <Text style={styles.label}>Change Password</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  container: { flex: 1, padding: 20 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderColor: '#eee',
  },
  label: { fontSize: 15, fontWeight: '600' },
  sublabel: { fontSize: 12, color: '#999', marginTop: 2 },
});
