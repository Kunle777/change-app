import { useState } from 'react';
import { Modal, View, Text, TouchableOpacity, Pressable, ActivityIndicator } from 'react-native';
import { BrainDump, ParsedTaskSuggestion } from '../../types/brainDump';
import { parseDump, convertDumpToTask } from '../../services/braindump';

export default function DumpDetailSheet({
  visible,
  dump,
  onClose,
  onConverted,
}: {
  visible: boolean;
  dump: BrainDump | null;
  onClose: () => void;
  onConverted: () => void;
}) {
  const [loading, setLoading] = useState(false);
  const [suggestion, setSuggestion] = useState<ParsedTaskSuggestion | null>(null);
  const [checked, setChecked] = useState(false);

  async function handleTurnIntoTask() {
    if (!dump) return;
    setLoading(true);
    setChecked(false);
    try {
      setSuggestion(await parseDump(dump.id));
      setChecked(true);
    } catch {
      setSuggestion(null);
      setChecked(true);
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirm() {
    if (!dump || !suggestion) return;
    try {
      await convertDumpToTask(dump.id, suggestion);
      onConverted();
      handleClose();
    } catch {
      // stays open, user can retry
    }
  }

  function handleClose() {
    setSuggestion(null);
    setChecked(false);
    onClose();
  }

  if (!dump) return null;

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={handleClose}>
      <Pressable style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.4)' }} onPress={handleClose}>
        <Pressable
          onPress={(e) => e.stopPropagation()}
          style={{
            marginTop: 'auto',
            backgroundColor: '#fff',
            borderTopLeftRadius: 20,
            borderTopRightRadius: 20,
            padding: 20,
            paddingBottom: 32,
          }}
        >
          <Text style={{ fontWeight: '700', marginBottom: 12 }}>Your thought</Text>
          <Text style={{ color: '#444', marginBottom: 20 }}>{dump.content}</Text>

          {!checked && !loading && dump.possible_task && (
            <TouchableOpacity
              onPress={handleTurnIntoTask}
              style={{
                backgroundColor: '#EEF0FF',
                borderRadius: 10,
                padding: 14,
                marginBottom: 10,
              }}
            >
              <Text style={{ color: '#4F46E5', fontWeight: '600', textAlign: 'center' }}>
                ✨ Turn into task
              </Text>
            </TouchableOpacity>
          )}

          {loading && <ActivityIndicator style={{ marginVertical: 12 }} />}

          {checked && suggestion && (
            <View
              style={{
                backgroundColor: '#F8FAFC',
                borderRadius: 10,
                padding: 14,
                marginBottom: 12,
              }}
            >
              <Text style={{ fontWeight: '600' }}>{suggestion.title}</Text>
              {suggestion.due_date && (
                <Text style={{ color: '#888', fontSize: 12, marginTop: 4 }}>
                  📅 {suggestion.due_date} {suggestion.time ?? ''}
                </Text>
              )}
              <TouchableOpacity
                onPress={handleConfirm}
                style={{ backgroundColor: '#4F46E5', borderRadius: 10, padding: 12, marginTop: 10 }}
              >
                <Text style={{ color: '#fff', fontWeight: '600', textAlign: 'center' }}>
                  Add task
                </Text>
              </TouchableOpacity>
            </View>
          )}

          {checked && !suggestion && (
            <Text style={{ color: '#888', marginBottom: 12 }}>
              ELVYN couldn't find a clear task in this one.
            </Text>
          )}

          <TouchableOpacity onPress={handleClose}>
            <Text style={{ color: '#888', textAlign: 'center' }}>Keep as dump</Text>
          </TouchableOpacity>
        </Pressable>
      </Pressable>
    </Modal>
  );
}
