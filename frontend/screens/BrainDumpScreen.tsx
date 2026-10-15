import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Alert,
  Pressable,
  RefreshControl,
  StyleSheet,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';

import BrainDumpCard from '../components/braindump/BrainDumpCard';
import DumpDetailSheet from '../components/braindump/DumpDetailSheet';
import EditDumpSheet from '../components/braindump/EditDumpSheet';
import ElvynMascot from '../components/ElvynMascot';
import VoiceCaptureButton from '../components/VoiceCaptureButton';

import { createBrainDump, deleteBrainDump, getRecentDumps } from '../services/braindump';
import { BrainDump } from '../types/brainDump';

export default function BrainDumpScreen() {
  const [content, setContent] = useState('');
  const [source, setSource] = useState<'text' | 'voice'>('text');
  const [dumps, setDumps] = useState<BrainDump[]>([]);
  const [saving, setSaving] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const [activeDump, setActiveDump] = useState<BrainDump | null>(null);
  const [sheetVisible, setSheetVisible] = useState(false);
  const [menuDump, setMenuDump] = useState<BrainDump | null>(null);
  const [editingDump, setEditingDump] = useState<BrainDump | null>(null);
  const [deleting, setDeleting] = useState(false);

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

  const handleDelete = async (dump: BrainDump) => {
    setDeleting(true);
    try {
      await deleteBrainDump(dump.id);
      setDumps((current) => current.filter((item) => item.id !== dump.id));
      setMenuDump(null);
      if (activeDump?.id === dump.id) {
        setSheetVisible(false);
        setActiveDump(null);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Could not delete this brain dump.';
      if (Platform.OS === 'web') {
        window.alert(message);
      } else {
        Alert.alert('Could not delete brain dump', message);
      }
    } finally {
      setDeleting(false);
    }
  };

  const confirmDelete = (dump: BrainDump) => {
    setMenuDump(null);
    if (Platform.OS === 'web') {
      if (window.confirm('Delete this brain dump? This will also remove it from AI memory.')) {
        void handleDelete(dump);
      }
      return;
    }

    Alert.alert(
      'Delete brain dump?',
      'This will also remove it from AI memory.',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Delete', style: 'destructive', onPress: () => void handleDelete(dump) },
      ],
    );
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
              <Text style={styles.inputLabel}>What&apos;s on your mind?</Text>
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
            onMorePress={() => setMenuDump(item)}
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

      <Modal
        visible={menuDump !== null}
        transparent
        animationType="fade"
        onRequestClose={() => setMenuDump(null)}
      >
        <Pressable
          onPress={() => setMenuDump(null)}
          style={{
            flex: 1,
            justifyContent: 'center',
            paddingHorizontal: 32,
            backgroundColor: 'rgba(0,0,0,0.35)',
          }}
        >
          <Pressable
            onPress={(event) => event.stopPropagation()}
            style={{ backgroundColor: '#fff', borderRadius: 16, padding: 8 }}
          >
            <Text style={{ paddingHorizontal: 12, paddingTop: 10, paddingBottom: 6, color: '#6B7280' }}>
              Brain dump options
            </Text>
            <TouchableOpacity
              accessibilityRole="button"
              onPress={() => {
                setEditingDump(menuDump);
                setMenuDump(null);
              }}
              style={{ padding: 14 }}
            >
              <Text style={{ color: '#111827', fontSize: 16 }}>Edit</Text>
            </TouchableOpacity>
            <TouchableOpacity
              accessibilityRole="button"
              disabled={deleting}
              onPress={() => menuDump && confirmDelete(menuDump)}
              style={{ padding: 14 }}
            >
              <Text style={{ color: '#DC2626', fontSize: 16 }}>
                {deleting ? 'Deleting…' : 'Delete'}
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              accessibilityRole="button"
              onPress={() => setMenuDump(null)}
              style={{ padding: 14 }}
            >
              <Text style={{ color: '#6B7280', fontSize: 16 }}>Cancel</Text>
            </TouchableOpacity>
          </Pressable>
        </Pressable>
      </Modal>

      {editingDump && (
        <EditDumpSheet
          visible
          dump={editingDump}
          onClose={() => setEditingDump(null)}
          onSaved={(updated) => {
            setDumps((current) => current.map((item) => (item.id === updated.id ? updated : item)));
            if (activeDump?.id === updated.id) setActiveDump(updated);
            setEditingDump(null);
          }}
        />
      )}
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
