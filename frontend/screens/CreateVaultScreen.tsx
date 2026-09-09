import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert } from 'react-native';
import DateTimePicker from '@react-native-community/datetimepicker';
import { createVault } from '../services/savings';

export default function CreateVaultScreen({ navigation }: any) {
  const [name, setName] = useState('');
  const [target, setTarget] = useState('');
  const [lockDate, setLockDate] = useState(new Date(Date.now() + 7 * 86400000));
  const [showPicker, setShowPicker] = useState(false);

  const handleCreate = async () => {
    const amount = parseFloat(target);
    if (!name || !amount || amount <= 0) {
      Alert.alert('Enter a name and a valid target amount');
      return;
    }
    try {
      await createVault({ name, target_amount: amount, lock_until: lockDate.toISOString() });
      navigation.replace('Savings');
    } catch (e: any) {
      Alert.alert('Could not create vault', e.message);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>New savings vault</Text>
      <TextInput style={styles.input} placeholder="Vault name (e.g. Rent Fund)" value={name} onChangeText={setName} />
      <TextInput style={styles.input} placeholder="Target amount (₦)" keyboardType="numeric" value={target} onChangeText={setTarget} />
      <TouchableOpacity style={styles.dateButton} onPress={() => setShowPicker(true)}>
        <Text>Lock until: {lockDate.toDateString()}</Text>
      </TouchableOpacity>
      {showPicker && (
        <DateTimePicker
          value={lockDate}
          mode="date"
          minimumDate={new Date(Date.now() + 7 * 86400000)}
          onChange={(event, date) => {
            setShowPicker(false);
            if (date instanceof Date) setLockDate(date); // real type guard — Android quirk from Phase 3.5
          }}
        />
      )}
      <TouchableOpacity style={styles.button} onPress={handleCreate}>
        <Text style={styles.buttonText}>Create vault</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24, paddingTop: 60 },
  title: { fontSize: 20, fontWeight: '700', marginBottom: 24 },
  input: { borderWidth: 1, borderColor: '#ccc', borderRadius: 8, padding: 12, marginBottom: 12 },
  dateButton: { borderWidth: 1, borderColor: '#ccc', borderRadius: 8, padding: 12, marginBottom: 20 },
  button: { backgroundColor: '#333', padding: 14, borderRadius: 8, alignItems: 'center' },
  buttonText: { color: '#fff', fontWeight: '600' },
});