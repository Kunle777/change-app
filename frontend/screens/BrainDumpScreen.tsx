import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Animated,
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  StyleSheet,
  Alert,
  RefreshControl,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import {
  createBrainDump,
  getBrainDumps,
  convertBrainDump,
  parseBrainDump,
} from '../services/braindump';
import type { ParsedTaskSuggestion } from '../services/braindump';
import VoiceCaptureButton from '../components/VoiceCaptureButton';
import ElvynMascot from '../components/ElvynMascot';

type Dump = {
  id: string;
  content: string;
  is_converted: boolean;
  created_at: string;
  converted_tasks?: { title: string; priority: string }[];
  suggestions?: ParsedTaskSuggestion[];
};

export default function BrainDumpScreen() {
  const [content, setContent] = useState('');
  const [dumps, setDumps] = useState<Dump[]>([]);
  const [saving, setSaving] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [convertingId, setConvertingId] = useState<string | null>(null);
  const [parsingId, setParsingId] = useState<string | null>(null);
  const [selectedSuggestions, setSelectedSuggestions] = useState<Record<string, number[]>>({});
  const [showSavedFlash, setShowSavedFlash] = useState(false);
  const flashOpacity = useRef(new Animated.Value(0)).current;

  const flashSaved = useCallback(() => {
    flashOpacity.stopAnimation();
    flashOpacity.setValue(0);
    setShowSavedFlash(true);
    Animated.sequence([
      Animated.timing(flashOpacity, { toValue: 1, duration: 200, useNativeDriver: true }),
      Animated.delay(1400),
      Animated.timing(flashOpacity, { toValue: 0, duration: 300, useNativeDriver: true }),
    ]).start(({ finished }) => {
      if (finished) setShowSavedFlash(false);
    });
  }, [flashOpacity]);

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

  useEffect(() => () => flashOpacity.stopAnimation(), [flashOpacity]);

  const handleSave = async () => {
    if (!content.trim()) return;
    setSaving(true);
    try {
      await createBrainDump(content.trim());
      setContent('');
      await loadDumps();
      flashSaved();
    } catch (err: any) {
      Alert.alert('Error', err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleParse = async (id: string) => {
    setParsingId(id);
    try {
      const suggestions = await parseBrainDump(id);
      setDumps((prev) => prev.map((dump) => dump.id === id ? { ...dump, suggestions } : dump));
      setSelectedSuggestions((prev) => ({ ...prev, [id]: suggestions.map((_, index) => index) }));
    } catch (err: any) {
      Alert.alert('Error', err.message);
    } finally {
      setParsingId(null);
    }
  };

  const toggleSuggestion = (id: string, index: number) => {
    setSelectedSuggestions((prev) => {
      const selected = prev[id] ?? [];
      return {
        ...prev,
        [id]: selected.includes(index)
          ? selected.filter((selectedIndex) => selectedIndex !== index)
          : [...selected, index],
      };
    });
  };

  const handleConvert = async (dump: Dump) => {
    const selected = selectedSuggestions[dump.id] ?? [];
    const suggestions = (dump.suggestions ?? []).filter((_, index) => selected.includes(index));
    if (suggestions.length === 0) {
      Alert.alert('Select tasks', 'Choose at least one suggestion to add.');
      return;
    }
    setConvertingId(dump.id);
    try {
      const tasks = await convertBrainDump(dump.id, suggestions);
      void import('../services/notifications').then(({ reconcileNotifications }) =>
        reconcileNotifications(),
      ).catch((error) => console.warn('Could not refresh reminders for converted tasks', error));
      setDumps((prev) =>
        prev.map((d) =>
          d.id === dump.id
            ? {
                ...d,
                is_converted: true,
              converted_tasks: tasks.map((t: any) => ({ title: t.title, priority: t.priority })),
              }
            : d,
        ),
      );
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
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <View style={styles.header}>
        <Text style={styles.title}>Brain Dump</Text>
        <Text style={styles.subtitle}>Get it out. Sort it later.</Text>
      </View>
      <View style={styles.composer}>
        <Text style={styles.composerTitle}>What's on your mind?</Text>
      <TextInput
        style={styles.input}
        value={content}
        onChangeText={setContent}
        placeholder="Type anything. Don't worry about organizing it yet."
        multiline
        maxLength={1000}
      />
      <VoiceCaptureButton onTranscript={(text) => setContent(text)} />
      </View>
      {showSavedFlash && (
        <Animated.View style={[styles.savedFlash, { opacity: flashOpacity }]}>
          <ElvynMascot variant="neutral" size={32} />
          <Text style={styles.savedFlashText}>Got it. It's here.</Text>
        </Animated.View>
      )}
      <TouchableOpacity
        style={[styles.saveButton, (!content.trim() || saving) && styles.saveButtonDisabled]}
        onPress={handleSave}
        disabled={saving || !content.trim()}
      >
        <Text style={styles.saveButtonText}>{saving ? 'Saving...' : 'Save'}</Text>
      </TouchableOpacity>
      <Text style={styles.recentTitle}>Recent</Text>

      <FlatList
        style={{ flex: 1 }}
        data={dumps}
        keyExtractor={(item) => item.id}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        contentContainerStyle={{ paddingTop: 8, paddingBottom: 24 }}
        ListEmptyComponent={
          <Text style={styles.empty}>Nothing dumped yet. Brain full? Let it out.</Text>
        }
        renderItem={({ item }) => (
          <View style={styles.dumpRow}>
            <Text style={styles.dumpText}>{item.content}</Text>
            {item.is_converted ? (
              <View>
                <Text style={styles.convertedLabel}>✓ Converted to tasks:</Text>
                {item.converted_tasks?.map((t, i) => (
                  <Text key={i} style={styles.taskTitle}>
                    • {t.title} ({t.priority})
                  </Text>
                ))}
              </View>
            ) : item.suggestions ? (
              <View style={styles.suggestions}>
                {item.suggestions.length > 0 && (
                  <View style={styles.suggestionHeading}>
                    <ElvynMascot variant="neutral" size={28} />
                    <Text style={styles.convertedLabel}>
                      ELVYN found {item.suggestions.length} possible task{item.suggestions.length === 1 ? '' : 's'}:
                    </Text>
                  </View>
                )}
                {item.suggestions.length === 0 ? (
                  <Text style={styles.taskTitle}>No actionable tasks found.</Text>
                ) : item.suggestions.map((suggestion, index) => {
                  const checked = (selectedSuggestions[item.id] ?? []).includes(index);
                  return (
                    <TouchableOpacity
                      key={`${index}-${suggestion.title}`}
                      style={styles.suggestionRow}
                      onPress={() => toggleSuggestion(item.id, index)}
                      accessibilityRole="checkbox"
                      accessibilityState={{ checked }}
                    >
                      <Text style={styles.checkbox}>{checked ? '☑' : '□'}</Text>
                      <Text style={styles.taskTitle}>
                        {suggestion.title} ({suggestion.priority})
                        {suggestion.recurrence_rule ? ` · ${suggestion.recurrence_rule.frequency}` : ''}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
                <TouchableOpacity
                  style={styles.convertButton}
                  onPress={() => handleConvert(item)}
                  disabled={convertingId === item.id || item.suggestions.length === 0}
                >
                  <Text style={styles.convertLink}>
                    {convertingId === item.id ? 'Adding...' : 'Add selected tasks'}
                  </Text>
                </TouchableOpacity>
              </View>
            ) : (
              <TouchableOpacity
                onPress={() => handleParse(item.id)}
                disabled={parsingId === item.id}
              >
                <Text style={styles.convertLink}>
                  {parsingId === item.id ? 'Finding tasks...' : 'Find tasks'}
                </Text>
              </TouchableOpacity>
            )}
          </View>
        )}
      />
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, paddingHorizontal: 20, paddingBottom: 12, backgroundColor: '#fff' },
  header: { paddingTop: 50, paddingBottom: 14 },
  title: { fontSize: 20, fontWeight: '700', color: '#222' },
  subtitle: { color: '#888', fontSize: 12, marginTop: 4 },
  composer: { backgroundColor: '#fff', borderRadius: 16, padding: 16, marginBottom: 8, borderWidth: 1, borderColor: '#eee' },
  composerTitle: { fontWeight: '600', marginBottom: 6, color: '#222' },
  input: {
    minHeight: 76,
    textAlignVertical: 'top',
    fontSize: 14,
    color: '#222',
  },
  saveButton: {
    backgroundColor: '#333',
    borderRadius: 10,
    padding: 12,
    alignItems: 'center',
    marginTop: 8,
    marginBottom: 16,
  },
  saveButtonDisabled: { backgroundColor: '#999' },
  saveButtonText: { color: '#fff', fontWeight: '600' },
  empty: { color: '#aaa', textAlign: 'center', marginTop: 40, fontSize: 14 },
  dumpRow: { borderBottomWidth: 1, borderColor: '#eee', paddingVertical: 12 },
  dumpText: { fontSize: 14, marginBottom: 6, color: '#222' },
  convertedLabel: { fontSize: 12, color: '#999', marginBottom: 2 },
  taskTitle: { fontSize: 12, color: '#3a6b4a', marginLeft: 4 },
  convertLink: { fontSize: 12, color: '#3a6b4a', fontWeight: '600' },
  suggestions: { marginTop: 4 },
  suggestionRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 6 },
  checkbox: { width: 26, color: '#3a6b4a', fontSize: 18 },
  convertButton: { paddingVertical: 8, alignSelf: 'flex-start' },
  savedFlash: { flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: '#EEF0FF', borderRadius: 12, padding: 10, marginBottom: 12 },
  savedFlashText: { color: '#4F46E5', fontSize: 13 },
  recentTitle: { color: '#222', fontWeight: '700', marginBottom: 4 },
  suggestionHeading: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 8 },
});
