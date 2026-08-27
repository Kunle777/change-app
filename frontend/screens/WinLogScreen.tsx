import { useEffect, useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { getWins, createWin } from '../services/wins';

type Win = {
  id: string;
  description: string;
  created_at: string;
};

export default function WinLogScreen() {
  const [wins, setWins] = useState<Win[]>([]);
  const [streak, setStreak] = useState(0);
  const [loading, setLoading] = useState(true);
  const [newWin, setNewWin] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const data = await getWins();
      setWins(data.wins);
      setStreak(data.streak);
    } catch (err) {
      console.log('load wins error:', err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleAddWin() {
    if (!newWin.trim()) return;
    setSubmitting(true);
    try {
      await createWin(newWin.trim());
      setNewWin('');
      await load(); // reload so streak recalculates against the real new row
    } catch (err) {
      console.log('createWin error:', err);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <View style={styles.container}>
      <View style={styles.streakBox}>
        <Text style={styles.streakText}>🔥 {streak}-day streak</Text>
      </View>

      <TextInput
        style={styles.input}
        placeholder="Today's small win..."
        value={newWin}
        onChangeText={setNewWin}
      />
      <TouchableOpacity style={styles.addButton} onPress={handleAddWin} disabled={submitting}>
        <Text style={styles.addButtonText}>{submitting ? 'Saving...' : 'Log Win'}</Text>
      </TouchableOpacity>

      {loading ? (
        <ActivityIndicator style={{ marginTop: 20 }} />
      ) : (
        <FlatList
          data={wins}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <View style={styles.winRow}>
              <Text style={styles.winText}>{item.description}</Text>
              <Text style={styles.winDate}>{new Date(item.created_at).toLocaleDateString()}</Text>
            </View>
          )}
          ListEmptyComponent={<Text style={styles.emptyText}>No wins logged yet.</Text>}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 20, backgroundColor: '#fff' },
  streakBox: {
    backgroundColor: '#ddeee0',
    borderRadius: 10,
    padding: 14,
    marginBottom: 16,
    alignItems: 'center',
  },
  streakText: { fontWeight: '700', color: '#3a6b4a', fontSize: 16 },
  input: {
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
  },
  addButton: {
    backgroundColor: '#333',
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
    marginBottom: 16,
  },
  addButtonText: { color: '#fff', fontWeight: '600' },
  winRow: {
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
    paddingVertical: 10,
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  winText: { flex: 1 },
  winDate: { color: '#999', fontSize: 12 },
  emptyText: { textAlign: 'center', color: '#999', marginTop: 30 },
});
