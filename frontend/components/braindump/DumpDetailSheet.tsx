import { useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { BrainDump, ParsedTaskSuggestion } from '../../types/brainDump';
import { parseDump, convertDumpToTask } from '../../services/braindump';
import { useColors } from '../../theme/colors';

const PRIORITIES: Array<ParsedTaskSuggestion['priority']> = ['low', 'medium', 'high'];
const AI_ERROR = "Couldn't get help with this just now. Check your connection and try again.";
const CONVERT_ERROR = "Couldn't add that task just now. Please try again.";

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
  const colors = useColors();
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
      console.warn('Could not prepare a task from brain dump:', parseError);
      setSuggestion(null);
      setError(AI_ERROR);
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
      console.warn('Could not convert brain dump to task:', convertError);
      setError(CONVERT_ERROR);
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
      <Pressable
        style={{ flex: 1, backgroundColor: colors.overlay }}
        onPress={handleClose}
        accessibilityRole="button"
        accessibilityLabel="Close brain dump details"
      >
        <KeyboardAvoidingView
          style={{ flex: 1, justifyContent: 'flex-end' }}
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        >
          <Pressable
            onPress={(event) => event.stopPropagation()}
            style={{
              marginTop: 'auto',
              maxHeight: '90%',
              backgroundColor: colors.surface,
              borderTopLeftRadius: 24,
              borderTopRightRadius: 24,
              overflow: 'hidden',
            }}
          >
            <ScrollView
              keyboardShouldPersistTaps="handled"
              contentContainerStyle={{ padding: 20, paddingBottom: 24 }}
            >
              <Text
                accessibilityRole="header"
                maxFontSizeMultiplier={1.2}
                style={{ color: colors.text, fontSize: 16, lineHeight: 22, fontWeight: '600', marginBottom: 12 }}
              >
                Your thought
              </Text>
              <Text
                maxFontSizeMultiplier={1.4}
                style={{ color: colors.text, fontSize: 14, lineHeight: 20, marginBottom: 20 }}
              >
                {dump.content}
              </Text>

              {!checked && !loading && dump.possible_task ? (
                <TouchableOpacity
                  onPress={() => void handleTurnIntoTask()}
                  accessibilityRole="button"
                  accessibilityLabel="Get help turning this into a task"
                  style={{
                    minHeight: 44,
                    flexDirection: 'row',
                    alignItems: 'center',
                    justifyContent: 'center',
                    backgroundColor: colors.primarySoft,
                    borderRadius: 12,
                    paddingHorizontal: 14,
                    marginBottom: 10,
                  }}
                >
                  <Ionicons name="sparkles-outline" size={17} color={colors.primary} />
                  <Text
                    maxFontSizeMultiplier={1.2}
                    style={{ color: colors.primary, fontSize: 14, lineHeight: 20, fontWeight: '600', marginLeft: 8 }}
                  >
                    Turn into task
                  </Text>
                </TouchableOpacity>
              ) : null}

              {loading ? <ActivityIndicator color={colors.primary} style={{ marginVertical: 12 }} /> : null}

              {checked && suggestion ? (
                <View
                  style={{
                    backgroundColor: colors.background,
                    borderColor: colors.border,
                    borderWidth: 1,
                    borderRadius: 14,
                    padding: 14,
                    marginBottom: 12,
                  }}
                >
                  {editing ? (
                    <>
                      <Text maxFontSizeMultiplier={1.2} style={{ color: colors.textMuted, fontSize: 12, lineHeight: 16, marginBottom: 4 }}>
                        Task title
                      </Text>
                      <TextInput
                        value={suggestion.title}
                        onChangeText={(title) => setSuggestion({ ...suggestion, title })}
                        maxLength={200}
                        maxFontSizeMultiplier={1.4}
                        accessibilityLabel="Task title"
                        style={{
                          minHeight: 44,
                          backgroundColor: colors.surface,
                          borderColor: colors.border,
                          borderWidth: 1,
                          borderRadius: 10,
                          padding: 10,
                          marginBottom: 10,
                          color: colors.text,
                          fontSize: 14,
                        }}
                      />
                      <Text maxFontSizeMultiplier={1.2} style={{ color: colors.textMuted, fontSize: 12, lineHeight: 16, marginBottom: 4 }}>
                        Due date (optional)
                      </Text>
                      <TextInput
                        value={suggestion.due_date ?? ''}
                        onChangeText={(due_date) => setSuggestion({ ...suggestion, due_date: due_date || null })}
                        placeholder="YYYY-MM-DD"
                        placeholderTextColor={colors.textMuted}
                        autoCapitalize="none"
                        maxFontSizeMultiplier={1.4}
                        accessibilityLabel="Due date"
                        style={{
                          minHeight: 44,
                          backgroundColor: colors.surface,
                          borderColor: colors.border,
                          borderWidth: 1,
                          borderRadius: 10,
                          padding: 10,
                          marginBottom: 10,
                          color: colors.text,
                          fontSize: 14,
                        }}
                      />
                      <Text maxFontSizeMultiplier={1.2} style={{ color: colors.textMuted, fontSize: 12, lineHeight: 16, marginBottom: 4 }}>
                        Reminder time (optional)
                      </Text>
                      <TextInput
                        value={suggestion.time ?? ''}
                        onChangeText={(time) => setSuggestion({ ...suggestion, time: time || null })}
                        placeholder="HH:MM"
                        placeholderTextColor={colors.textMuted}
                        autoCapitalize="none"
                        maxFontSizeMultiplier={1.4}
                        accessibilityLabel="Reminder time"
                        style={{
                          minHeight: 44,
                          backgroundColor: colors.surface,
                          borderColor: colors.border,
                          borderWidth: 1,
                          borderRadius: 10,
                          padding: 10,
                          marginBottom: 10,
                          color: colors.text,
                          fontSize: 14,
                        }}
                      />
                      <Text maxFontSizeMultiplier={1.2} style={{ color: colors.textMuted, fontSize: 12, lineHeight: 16, marginBottom: 6 }}>
                        Priority
                      </Text>
                      <View style={{ flexDirection: 'row', gap: 8, marginBottom: 8 }}>
                        {PRIORITIES.map((priority) => (
                          <TouchableOpacity
                            key={priority}
                            onPress={() => setSuggestion({ ...suggestion, priority })}
                            accessibilityRole="button"
                            accessibilityLabel={`${priority} priority`}
                            accessibilityState={{ selected: suggestion.priority === priority }}
                            style={{
                              flex: 1,
                              minHeight: 44,
                              borderRadius: 10,
                              alignItems: 'center',
                              justifyContent: 'center',
                              backgroundColor: suggestion.priority === priority ? colors.primarySoft : colors.surface,
                              borderWidth: 1,
                              borderColor: suggestion.priority === priority ? colors.primary : colors.border,
                            }}
                          >
                            <Text maxFontSizeMultiplier={1.2} style={{ color: colors.text, fontSize: 14, lineHeight: 20, textTransform: 'capitalize' }}>
                              {priority}
                            </Text>
                          </TouchableOpacity>
                        ))}
                      </View>
                    </>
                  ) : (
                    <>
                      <Text maxFontSizeMultiplier={1.4} style={{ color: colors.text, fontSize: 14, lineHeight: 20, fontWeight: '600' }}>
                        {suggestion.title}
                      </Text>
                      <Text maxFontSizeMultiplier={1.2} style={{ color: colors.textMuted, fontSize: 12, lineHeight: 16, marginTop: 4 }}>
                        {suggestion.due_date || suggestion.time
                          ? `${suggestion.due_date ?? 'No due date'} ${suggestion.time ?? ''}`
                          : 'No due date or reminder'}
                        {' · '}
                        {suggestion.priority} priority
                      </Text>
                    </>
                  )}
                  <TouchableOpacity
                    onPress={() => setEditing(!editing)}
                    accessibilityRole="button"
                    accessibilityLabel={editing ? 'Finish editing task' : 'Edit suggested task'}
                    style={{ minHeight: 44, justifyContent: 'center' }}
                  >
                    <Text maxFontSizeMultiplier={1.2} style={{ color: colors.primary, textAlign: 'center', fontWeight: '600', fontSize: 14 }}>
                      {editing ? 'Done editing' : 'Edit task'}
                    </Text>
                  </TouchableOpacity>
                  {error ? (
                    <Text accessibilityRole="alert" maxFontSizeMultiplier={1.4} style={{ color: colors.danger, fontSize: 13, lineHeight: 18, marginBottom: 8 }}>
                      {error}
                    </Text>
                  ) : null}
                  <TouchableOpacity
                    onPress={() => void handleConfirm()}
                    disabled={loading || !suggestion.title.trim()}
                    accessibilityRole="button"
                    accessibilityLabel="Add task"
                    style={{
                      minHeight: 44,
                      justifyContent: 'center',
                      backgroundColor: colors.primary,
                      borderRadius: 12,
                      opacity: loading || !suggestion.title.trim() ? 0.6 : 1,
                    }}
                  >
                    {loading ? (
                      <ActivityIndicator color={colors.surface} />
                    ) : (
                      <Text maxFontSizeMultiplier={1.2} style={{ color: colors.surface, fontWeight: '600', textAlign: 'center', fontSize: 14, lineHeight: 20 }}>
                        Add task
                      </Text>
                    )}
                  </TouchableOpacity>
                </View>
              ) : null}

              {checked && !suggestion && !error ? (
                <Text maxFontSizeMultiplier={1.4} style={{ color: colors.textMuted, fontSize: 14, lineHeight: 20, marginBottom: 12 }}>
                  Elvyn couldn&apos;t find a clear task in this one.
                </Text>
              ) : null}
              {error && !suggestion ? (
                <Text accessibilityRole="alert" maxFontSizeMultiplier={1.4} style={{ color: colors.danger, fontSize: 14, lineHeight: 20, marginBottom: 12 }}>
                  {error}
                </Text>
              ) : null}

              <TouchableOpacity
                onPress={handleClose}
                accessibilityRole="button"
                accessibilityLabel="Keep as brain dump"
                style={{ minHeight: 44, alignItems: 'center', justifyContent: 'center' }}
              >
                <Text maxFontSizeMultiplier={1.2} style={{ color: colors.textMuted, textAlign: 'center', fontSize: 14, lineHeight: 20 }}>
                  Keep as dump
                </Text>
              </TouchableOpacity>
            </ScrollView>
          </Pressable>
        </KeyboardAvoidingView>
      </Pressable>
    </Modal>
  );
}
