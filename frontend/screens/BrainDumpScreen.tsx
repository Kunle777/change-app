import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, FlatList,
  StyleSheet, Alert, RefreshControl,
} from 'react-native';
import { createBrainDump, getBrainDumps, convertBrainDump } from '../services/braindump';

type Dump = {
  id: string;
  content: string;
  is_converted: boolean;
  created_at: string;
};

export default function BrainDumpScreen() {
  const [content, setContent] = useState('');
  const [dumps, setDumps] = useState<Dump[]>([]);
  const [saving, setSaving] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [convertingId, setConvertingId] = useState<string | null>(null);

  const loadDumps = useCallback(async () => {
    try {
      const data = await getBrainDumps();
      setDumps(data);
    } catch (err: any) {
      Alert.alert('Error', err.message);
    }
  }, []);

  useEffect(() => {
    loadDumps();
  }, [loadDumps]);

  const handleSave = async () => {
    if (!content.trim()) return;
    setSaving(true);
    try {
      await createBrainDump(content.trim());
      setContent('');
      await loadDumps();
    } catch (err: any) {
      Alert.alert('Error', err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleConvert = async (id: string) => {
    setConvertingId(id);
    try {
      const tasks = await convertBrainDump(id);
      Alert.alert('Converted', `Created ${tasks.length} task${tasks.length === 1 ? '' : 's'}`);
      await loadDumps();
    } catch (err: any) {
      Alert.alert('Error', err.message);
    } finally {
      setConvertingId(null);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadDumps();
    setRefreshing(false);
  };

  return (
    <View style={styles.container}>
      <TextInput
        style={styles.input}
        value={content}
        onChangeText={setContent}
        placeholder="Dump anything on your mind..."
        multiline
      />
      <TouchableOpacity
        style={[styles.saveButton, (!content.trim() || saving) && styles.saveButtonDisabled]}
        onPress={handleSave}
        disabled={saving || !content.trim()}
      >
        <Text style={styles.saveButtonText}>{saving ? 'Saving...' : 'Save'}</Text>
      </TouchableOpacity>

      <FlatList
        data={dumps}
        keyExtractor={(item) => item.id}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        contentContainerStyle={{ paddingTop: 16 }}
        ListEmptyComponent={<Text style={styles.empty}>Nothing dumped yet. Brain full? Let it out.</Text>}
        renderItem={({ item }) => (
          <View style={styles.dumpRow}>
            <Text style={styles.dumpText}>{item.content}</Text>
            {item.is_converted ? (
              <Text style={styles.convertedLabel}>✓ Converted to task</Text>
            ) : (
              <TouchableOpacity
                onPress={() => handleConvert(item.id)}
                disabled={convertingId === item.id}
              >
                <Text style={styles.convertLink}>
                  {convertingId === item.id ? 'Converting...' : 'Convert to task(s)'}
                </Text>
              </TouchableOpacity>
            )}
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: '#fff' },
  input: {
    borderWidth: 1, borderColor: '#ccc', borderRadius: 10,
    padding: 12, minHeight: 70, textAlignVertical: 'top', fontSize: 14,
  },
  saveButton: {
    backgroundColor: '#333', borderRadius: 10, padding: 12,
    alignItems: 'center', marginTop: 8,
  },
  saveButtonDisabled: { backgroundColor: '#999' },
  saveButtonText: { color: '#fff', fontWeight: '600' },
  empty: { color: '#aaa', textAlign: 'center', marginTop: 40, fontSize: 14 },
  dumpRow: { borderBottomWidth: 1, borderColor: '#eee', paddingVertical: 12 },
  dumpText: { fontSize: 14, marginBottom: 6, color: '#222' },
  convertedLabel: { fontSize: 12, color: '#999' },
  convertLink: { fontSize: 12, color: '#3a6b4a', fontWeight: '600' },
});
