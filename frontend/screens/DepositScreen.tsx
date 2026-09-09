// screens/DepositScreen.tsx
import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert, Clipboard } from 'react-native';
import { createDepositIntent } from '../services/savings';

export default function DepositScreen({ route }: any) {
  const { vaultId, vaultName } = route.params;
  const [amount, setAmount] = useState('');
  const [intent, setIntent] = useState<any>(null);

  const handleGetAccount = async () => {
    const value = parseFloat(amount);
    if (!value || value <= 0) {
      Alert.alert('Enter a valid amount');
      return;
    }
    try {
      const result = await createDepositIntent(vaultId, value);
      setIntent(result);
    } catch (e: any) {
      Alert.alert('Could not start deposit', e.message);
    }
  };

  if (intent) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>Transfer to fund "{vaultName}"</Text>
        <View style={styles.card}>
          <Text style={styles.label}>Account Number</Text>
          <TouchableOpacity onPress={() => Clipboard.setString(intent.account_number)}>
            <Text style={styles.accountNumber}>{intent.account_number}</Text>
          </TouchableOpacity>
          <Text style={styles.label}>Bank</Text>
          <Text style={styles.value}>{intent.bank_name}</Text>
          <Text style={styles.label}>Account Name</Text>
          <Text style={styles.value}>{intent.account_name}</Text>
          <Text style={styles.label}>Amount to transfer</Text>
          <Text style={styles.value}>₦{intent.amount_to_transfer} (includes ₦{intent.fee} fee)</Text>
        </View>
        <Text style={styles.expiry}>This deposit request expires in 30 minutes.</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Deposit into "{vaultName}"</Text>
      <TextInput style={styles.input} placeholder="Amount (₦)" keyboardType="numeric" value={amount} onChangeText={setAmount} />
      <TouchableOpacity style={styles.button} onPress={handleGetAccount}>
        <Text style={styles.buttonText}>Get account details</Text>
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
  card: { backgroundColor: '#f5f5f5', borderRadius: 12, padding: 16 },
  label: { fontSize: 11, color: '#999', marginTop: 12, textTransform: 'uppercase' },
  value: { fontSize: 15, fontWeight: '600' },
  accountNumber: { fontSize: 22, fontWeight: '700', letterSpacing: 1 },
  expiry: { fontSize: 12, color: '#c77', marginTop: 16, textAlign: 'center' },
});