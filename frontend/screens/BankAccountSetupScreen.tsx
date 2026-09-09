import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert, ActivityIndicator } from 'react-native';
import { setupBankAccount } from '../services/savings';

export default function BankAccountSetupScreen({ navigation }: any) {
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [bvn, setBvn] = useState('');
  const [bankCode, setBankCode] = useState('');
  const [accountNumber, setAccountNumber] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (bvn.length !== 11 || accountNumber.length !== 10) {
      Alert.alert('BVN must be 11 digits, account number 10 digits');
      return;
    }
    setLoading(true);
    try {
      await setupBankAccount({
        first_name: firstName, last_name: lastName,
        bvn, bank_code: bankCode, account_number: accountNumber,
      });
      Alert.alert(
        'Verification in progress',
        "We're confirming your identity. This usually takes a moment — you'll be notified when it's done.",
        [{ text: 'OK', onPress: () => navigation.replace('Home') }]
      );
    } catch (e: any) {
      Alert.alert('Something went wrong', e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Verify your identity</Text>
      <Text style={styles.sub}>Required once, before creating your first vault.</Text>
      <TextInput style={styles.input} placeholder="First name" value={firstName} onChangeText={setFirstName} />
      <TextInput style={styles.input} placeholder="Last name" value={lastName} onChangeText={setLastName} />
      <TextInput style={styles.input} placeholder="BVN" keyboardType="number-pad" maxLength={11} value={bvn} onChangeText={setBvn} />
      <TextInput style={styles.input} placeholder="Bank code (e.g. 057)" value={bankCode} onChangeText={setBankCode} />
      <TextInput style={styles.input} placeholder="Account number" keyboardType="number-pad" maxLength={10} value={accountNumber} onChangeText={setAccountNumber} />
      <TouchableOpacity style={styles.button} onPress={handleSubmit} disabled={loading}>
        {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.buttonText}>Verify</Text>}
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24, paddingTop: 60 },
  title: { fontSize: 20, fontWeight: '700', marginBottom: 4 },
  sub: { fontSize: 13, color: '#888', marginBottom: 24 },
  input: { borderWidth: 1, borderColor: '#ccc', borderRadius: 8, padding: 12, marginBottom: 12 },
  button: { backgroundColor: '#333', padding: 14, borderRadius: 8, alignItems: 'center', marginTop: 12 },
  buttonText: { color: '#fff', fontWeight: '600' },
});