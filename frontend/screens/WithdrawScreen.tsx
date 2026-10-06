import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert } from 'react-native';
import { requestWithdrawal } from '../services/savings';

export default function WithdrawScreen({ route, navigation }: any) {
  const { vaultId, vaultName } = route.params;
  const [amount, setAmount] = useState('');
  const [pin, setPin] = useState('');

  const handleWithdraw = async () => {
    const value = parseFloat(amount);
    if (!value || value <= 0 || pin.length !== 6) {
      Alert.alert('Enter a valid amount and 6-digit PIN');
      return;
    }
    try {
      await requestWithdrawal(vaultId, value, pin);
      Alert.alert('Withdrawal initiated', 'Funds are on the way to your bank account.', [
        { text: 'OK', onPress: () => navigation.goBack() },
      ]);
    } catch (e: any) {
      Alert.alert('Withdrawal failed', e.message);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Withdraw from "{vaultName}"</Text>
      <TextInput style={styles.input} placeholder="Amount (₦)" keyboardType="numeric" value={amount} onChangeText={setAmount} />
      <TextInput style={styles.input} placeholder="Withdrawal PIN" keyboardType="number-pad" secureTextEntry maxLength={6} value={pin} onChangeText={setPin} />
      <TouchableOpacity style={styles.button} onPress={handleWithdraw}>
        <Text style={styles.buttonText}>Withdraw</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24, paddingTop: 60 },
  title: { fontSize: 18, fontWeight: '700', marginBottom: 20 },
  input: { borderWidth: 1, borderColor: '#ccc', borderRadius: 8, padding: 12, marginBottom: 12 },
  button: { backgroundColor: '#333', padding: 14, borderRadius: 8, alignItems: 'center' },
  buttonText: { color: '#fff', fontWeight: '600' },
});