// screens/SavingsScreen.tsx
import React, { useEffect, useState, useCallback } from 'react';
import { View, Text, FlatList, TouchableOpacity, StyleSheet, RefreshControl } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { listVaults } from '../services/savings';

export default function SavingsScreen({ navigation }: any) {
  const [vaults, setVaults] = useState<any[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  const load = async () => {
    const data = await listVaults();
    setVaults(data);
  };

  useFocusEffect(useCallback(() => { load(); }, []));

  const onRefresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  return (
    <View style={styles.container}>
      <FlatList
        data={vaults}
        keyExtractor={(item) => item.id}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        renderItem={({ item }) => {
          const pct = Math.min(100, (item.current_amount / item.target_amount) * 100);
          return (
            <TouchableOpacity style={styles.card} onPress={() => navigation.navigate('Deposit', { vaultId: item.id, vaultName: item.name })}>
              <Text style={styles.name}>{item.name}</Text>
              <View style={styles.progressBar}>
                <View style={[styles.progressFill, { width: `${pct}%` }]} />
              </View>
              <Text style={styles.amount}>₦{item.current_amount.toLocaleString()} / ₦{item.target_amount.toLocaleString()}</Text>
              <Text style={styles.status}>{item.status.replace('_', ' ')}</Text>
            </TouchableOpacity>
          );
        }}
      />
      <TouchableOpacity style={styles.fab} onPress={() => navigation.navigate('CreateVault')}>
        <Text style={styles.fabText}>+</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, paddingTop: 50 },
  card: { backgroundColor: '#f5f5f5', borderRadius: 12, padding: 16, marginBottom: 12 },
  name: { fontSize: 16, fontWeight: '600', marginBottom: 8 },
  progressBar: { height: 8, backgroundColor: '#ddd', borderRadius: 4, overflow: 'hidden', marginBottom: 8 },
  progressFill: { height: '100%', backgroundColor: '#3a6b4a' },
  amount: { fontSize: 13, color: '#555' },
  status: { fontSize: 11, color: '#999', marginTop: 4, textTransform: 'capitalize' },
  fab: { position: 'absolute', bottom: 24, right: 24, width: 56, height: 56, borderRadius: 28, backgroundColor: '#333', justifyContent: 'center', alignItems: 'center' },
  fabText: { color: '#fff', fontSize: 28 },
});