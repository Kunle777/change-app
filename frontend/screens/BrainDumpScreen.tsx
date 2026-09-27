import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Alert,
  RefreshControl,
  StyleSheet,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';

import BrainDumpCard from '../components/braindump/BrainDumpCard';
import DumpDetailSheet from '../components/braindump/DumpDetailSheet';
import ElvynMascot from '../components/ElvynMascot';
import VoiceCaptureButton from '../components/VoiceCaptureButton';

import { createBrainDump, getRecentDumps } from '../services/braindump';
import { BrainDump } from '../types/brainDump';

export default function BrainDumpScreen() {
  const [content, setContent] = useState('');
  const [source, setSource] = useState<'text' | 'voice'>('text');
  const [dumps, setDumps] = useState<BrainDump[]>([]);
  const [saving, setSaving] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const [activeDump, setActiveDump] = useState<BrainDump | null>(null);
  const [sheetVisible, setSheetVisible] = useState(false);

  const loadDumps = useCallback(async () => {
    try {
      const data = await getRecentDumps();
      setDumps(data);
    } catch (err: any) {
      console.log('Failed to load dumps:', err);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      loadDumps();
    }, [loadDumps]),
  );

  const handleSave = async () => {
    if (!content.trim()) return;
    setSaving(true);
    try {
      await createBrainDump(content.trim(), source);
      setContent('');
      setSource('text');
      await loadDumps();
    } catch (err: any) {
      Alert.alert('Error', err.message || "Couldn't save your thought.");
    } finally {
      setSaving(false);
    }
  };

  const handleVoiceTranscript = (text: string) => {
    setContent(text);
    setSource('voice');
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

      <View style={styles.inputContainer}>
        <View style={styles.card}>
          <View style={styles.inputRow}>
            <ElvynMascot variant="neutral" size={40} />
            <View style={styles.inputFlex}>
              <Text style={styles.inputLabel}>What's on your mind?</Text>
              <TextInput
                value={content}
                onChangeText={(text) => {
                  setContent(text);
                  if (source === 'voice') setSource('text');
                }}
                placeholder="Type or speak anything. Don't worry about organizing it yet."
                multiline
                maxLength={1000}
                style={styles.textInput}
              />
            </View>
          </View>

          <View style={styles.voiceRow}>
            <VoiceCaptureButton onTranscript={handleVoiceTranscript} />
          </View>
        </View>

        <TouchableOpacity
          onPress={handleSave}
          disabled={saving || !content.trim()}
          style={[styles.saveButton, (saving || !content.trim()) && styles.saveButtonDisabled]}
        >
          <Text style={styles.saveButtonText}>{saving ? 'Saving…' : 'Save'}</Text>
        </TouchableOpacity>

        <Text style={styles.sectionTitle}>Recent</Text>
      </View>

      <FlatList
        data={dumps}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listPadding}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        renderItem={({ item }) => (
          <BrainDumpCard
            dump={item}
            onPress={() => {
              setActiveDump(item);
              setSheetVisible(true);
            }}
          />
        )}
        ListEmptyComponent={
          <Text style={styles.emptyText}>Nothing dumped yet. Brain full? Let it out.</Text>
        }
      />

      <DumpDetailSheet
        visible={sheetVisible}
        dump={activeDump}
        onClose={() => setSheetVisible(false)}
        onConverted={loadDumps}
      />
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F9FAFB',
  },
  header: {
    paddingHorizontal: 20,
    paddingTop: 50,
    paddingBottom: 10,
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
    color: '#111827',
  },
  subtitle: {
    color: '#6B7280',
    fontSize: 13,
    marginTop: 2,
  },
  inputContainer: {
    paddingHorizontal: 20,
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  inputRow: {
    flexDirection: 'row',
    gap: 12,
  },
  inputFlex: {
    flex: 1,
  },
  inputLabel: {
    fontWeight: '600',
    color: '#1F2937',
    marginBottom: 6,
  },
  textInput: {
    minHeight: 70,
    fontSize: 14,
    textAlignVertical: 'top',
    color: '#111827',
  },
  voiceRow: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    marginTop: 8,
    borderTopWidth: 1,
    borderTopColor: '#F3F4F6',
    paddingTop: 8,
  },
  saveButton: {
    backgroundColor: '#4F46E5',
    borderRadius: 12,
    padding: 14,
    alignItems: 'center',
    marginBottom: 20,
  },
  saveButtonDisabled: {
    opacity: 0.5,
  },
  saveButtonText: {
    color: '#FFFFFF',
    fontWeight: '600',
    fontSize: 15,
  },
  sectionTitle: {
    fontWeight: '700',
    fontSize: 16,
    color: '#111827',
    marginBottom: 10,
  },
  listPadding: {
    paddingHorizontal: 20,
    paddingBottom: 30,
  },
  emptyText: {
    color: '#9CA3AF',
    textAlign: 'center',
    marginTop: 24,
    fontSize: 14,
  },
});
