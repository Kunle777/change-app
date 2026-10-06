import React, { useState } from 'react';
import { View, Text, TextInput, StyleSheet, Alert } from 'react-native';
import { verifyPasscode } from '../services/passcode';

export default function PasscodeLockScreen({ onUnlock }: { onUnlock: () => void }) {
  const [code, setCode] = useState('');

  const handleChange = async (value: string) => {
    setCode(value);
    if (value.length >= 4) {
      const valid = await verifyPasscode(value);
      if (valid) {
        onUnlock();
      } else if (value.length === 6) {
        Alert.alert('Incorrect passcode');
        setCode('');
      }
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Enter passcode</Text>
      <TextInput
        style={styles.input}
        keyboardType="number-pad"
        secureTextEntry
        maxLength={6}
        value={code}
        onChangeText={handleChange}
        autoFocus
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#111' },
  title: { fontSize: 18, color: '#fff', marginBottom: 24 },
  input: { fontSize: 32, letterSpacing: 12, textAlign: 'center', borderBottomWidth: 2, borderColor: '#fff', color: '#fff', width: 200 },
});