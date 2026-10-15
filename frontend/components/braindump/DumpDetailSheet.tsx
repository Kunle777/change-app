import { useState } from 'react';
import {
  Modal,
  View,
  Text,
  TouchableOpacity,
  Pressable,
  ActivityIndicator,
  ScrollView,
  TextInput,
} from 'react-native';
import { BrainDump, ParsedTaskSuggestion } from '../../types/brainDump';
import { parseDump, convertDumpToTask } from '../../services/braindump';

const PRIORITIES: Array<ParsedTaskSuggestion['priority']> = ['low', 'medium', 'high'];

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
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleTurnIntoTask() {
    if (!dump) return;
    setLoading(true);
    setChecked(false);
    setError(null);
    try {
      setSuggestion(await parseDump(dump.id));
    } catch (parseError) {
      setSuggestion(null);
      setError(parseError instanceof Error ? parseError.message : 'Could not prepare a task.');
    } finally {
      setChecked(true);
      setLoading(false);
    }
  }

  async function handleConfirm() {
    if (!dump || !suggestion) return;
    setLoading(true);
    setError(null);
    try {
      await convertDumpToTask(dump.id, suggestion);
      onConverted();
      handleClose();
    } catch (convertError) {
      setError(convertError instanceof Error ? convertError.message : 'Could not add this task.');
    } finally {
      setLoading(false);
    }
  }

  function handleClose() {
    setSuggestion(null);
    setChecked(false);
    setEditing(false);
    setError(null);
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
            maxHeight: '90%',
            backgroundColor: '#fff',
            borderTopLeftRadius: 20,
            borderTopRightRadius: 20,
            overflow: 'hidden',
          }}
        >
          <ScrollView
            keyboardShouldPersistTaps="handled"
            contentContainerStyle={{ padding: 20, paddingBottom: 32 }}
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
              {editing ? (
                <>
                  <Text style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>Task title</Text>
                  <TextInput
                    value={suggestion.title}
                    onChangeText={(title) => setSuggestion({ ...suggestion, title })}
                    maxLength={200}
                    style={{ backgroundColor: '#fff', borderRadius: 8, padding: 10, marginBottom: 10 }}
                  />
                  <Text style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>Due date (optional)</Text>
                  <TextInput
                    value={suggestion.due_date ?? ''}
                    onChangeText={(due_date) =>
                      setSuggestion({ ...suggestion, due_date: due_date || null })
                    }
                    placeholder="YYYY-MM-DD"
                    autoCapitalize="none"
                    style={{ backgroundColor: '#fff', borderRadius: 8, padding: 10, marginBottom: 10 }}
                  />
                  <Text style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>Reminder time (optional)</Text>
                  <TextInput
                    value={suggestion.time ?? ''}
                    onChangeText={(time) => setSuggestion({ ...suggestion, time: time || null })}
                    placeholder="HH:MM"
                    autoCapitalize="none"
                    style={{ backgroundColor: '#fff', borderRadius: 8, padding: 10, marginBottom: 10 }}
                  />
                  <Text style={{ fontSize: 12, color: '#666', marginBottom: 6 }}>Priority</Text>
                  <View style={{ flexDirection: 'row', gap: 8, marginBottom: 8 }}>
                    {PRIORITIES.map((priority) => (
                      <TouchableOpacity
                        key={priority}
                        onPress={() => setSuggestion({ ...suggestion, priority })}
                        style={{
                          flex: 1,
                          padding: 9,
                          borderRadius: 8,
                          alignItems: 'center',
                          backgroundColor: suggestion.priority === priority ? '#E0E7FF' : '#fff',
                        }}
                      >
                        <Text style={{ textTransform: 'capitalize' }}>{priority}</Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                </>
              ) : (
                <>
                  <Text style={{ fontWeight: '600' }}>{suggestion.title}</Text>
                  <Text style={{ color: '#888', fontSize: 12, marginTop: 4 }}>
                    {suggestion.due_date || suggestion.time
                      ? `📅 ${suggestion.due_date ?? 'No due date'} ${suggestion.time ?? ''}`
                      : 'No due date or reminder'}
                    {' · '}
                    {suggestion.priority} priority
                  </Text>
                </>
              )}
              <TouchableOpacity
                onPress={() => setEditing(!editing)}
                style={{ paddingVertical: 10 }}
              >
                <Text style={{ color: '#4F46E5', textAlign: 'center', fontWeight: '600' }}>
                  {editing ? 'Done editing' : 'Edit task'}
                </Text>
              </TouchableOpacity>
              {error && <Text style={{ color: '#B91C1C', marginBottom: 8 }}>{error}</Text>}
              <TouchableOpacity
                onPress={handleConfirm}
                disabled={loading || !suggestion.title.trim()}
                style={{
                  backgroundColor: loading ? '#818CF8' : '#4F46E5',
                  borderRadius: 10,
                  padding: 12,
                }}
              >
                <Text style={{ color: '#fff', fontWeight: '600', textAlign: 'center' }}>
                  {loading ? 'Adding task…' : 'Add task'}
                </Text>
              </TouchableOpacity>
            </View>
          )}

          {checked && !suggestion && !error && (
            <Text style={{ color: '#888', marginBottom: 12 }}>ELVYN couldn't find a clear task in this one.</Text>
          )}
          {error && !suggestion && <Text style={{ color: '#B91C1C', marginBottom: 12 }}>{error}</Text>}

          <TouchableOpacity onPress={handleClose}>
            <Text style={{ color: '#888', textAlign: 'center' }}>Keep as dump</Text>
          </TouchableOpacity>
          </ScrollView>
        </Pressable>
      </Pressable>
    </Modal>
  );
}
