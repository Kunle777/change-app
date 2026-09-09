import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert } from 'react-native';
import { setupWithdrawalPin } from '../services/savings';

export default function WithdrawalPinSetupScreen({ navigation }: any) {
  const [pin, setPin] = useState('');

  const handleSubmit = async () => {
    if (pin.length !== 6) {
      Alert.alert('PIN must be exactly 6 digits');
      return;
    }
    try {
      await setupWithdrawalPin(pin);
      navigation.goBack();
    } catch (e: any) {
      Alert.alert('Could not set PIN', e.message);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Set withdrawal PIN</Text>
      <Text style={styles.sub}>Required for any manual withdrawal. Different from your app passcode.</Text>
      <TextInput style={styles.input} keyboardType="number-pad" secureTextEntry maxLength={6} value={pin} onChangeText={setPin} />
      <TouchableOpacity style={styles.button} onPress={handleSubmit}>
        <Text style={styles.buttonText}>Set PIN</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24, paddingTop: 60 },
  title: { fontSize: 18, fontWeight: '700', marginBottom: 8 },
  sub: { fontSize: 13, color: '#888', marginBottom: 24 },
  input: { fontSize: 24, letterSpacing: 8, textAlign: 'center', borderBottomWidth: 2, marginBottom: 24 },
  button: { backgroundColor: '#333', padding: 14, borderRadius: 8, alignItems: 'center' },
  buttonText: { color: '#fff', fontWeight: '600' },
});