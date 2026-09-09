import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert } from 'react-native';
import { setPasscode } from '../services/passcode';

export default function PasscodeSetupScreen({ navigation }: any) {
  const [code, setCode] = useState('');
  const [confirm, setConfirm] = useState('');
  const [stage, setStage] = useState<'enter' | 'confirm'>('enter');

  const handleContinue = () => {
    if (stage === 'enter') {
      if (code.length < 4 || code.length > 6) {
        Alert.alert('Passcode must be 4-6 digits');
        return;
      }
      setStage('confirm');
      return;
    }
    if (confirm !== code) {
      Alert.alert('Passcodes do not match');
      setConfirm('');
      return;
    }
    setPasscode(code).then(() => navigation.replace('Home'));
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{stage === 'enter' ? 'Set your passcode' : 'Confirm your passcode'}</Text>
      <TextInput
        style={styles.input}
        keyboardType="number-pad"
        secureTextEntry
        maxLength={6}
        value={stage === 'enter' ? code : confirm}
        onChangeText={stage === 'enter' ? setCode : setConfirm}
        autoFocus
      />
      <TouchableOpacity style={styles.button} onPress={handleContinue}>
        <Text style={styles.buttonText}>Continue</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 24 },
  title: { fontSize: 18, fontWeight: '600', marginBottom: 24 },
  input: { fontSize: 32, letterSpacing: 12, textAlign: 'center', borderBottomWidth: 2, width: 200, marginBottom: 32 },
  button: { backgroundColor: '#333', paddingVertical: 14, paddingHorizontal: 40, borderRadius: 8 },
  buttonText: { color: '#fff', fontWeight: '600' },
});