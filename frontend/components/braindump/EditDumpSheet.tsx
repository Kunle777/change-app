import { useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { updateBrainDump } from '../../services/braindump';
import { BrainDump } from '../../types/brainDump';

export default function EditDumpSheet({
  visible,
  dump,
  onClose,
  onSaved,
}: {
  visible: boolean;
  dump: BrainDump | null;
  onClose: () => void;
  onSaved: (updated: BrainDump) => void;
}) {
  const [content, setContent] = useState(dump?.content ?? '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    if (!dump || !content.trim()) {
      setError('Your thought cannot be empty.');
      return;
    }

    setSaving(true);
    setError(null);
    try {
      onSaved(await updateBrainDump(dump.id, content.trim()));
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Could not save your changes.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      visible={visible && dump !== null}
      transparent
      animationType="slide"
      onRequestClose={onClose}
    >
      <Pressable
        onPress={onClose}
        style={{ flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(0,0,0,0.4)' }}
      >
        <Pressable
          onPress={(event) => event.stopPropagation()}
          style={{
            backgroundColor: '#fff',
            borderTopLeftRadius: 20,
            borderTopRightRadius: 20,
            padding: 20,
            paddingBottom: 32,
          }}
        >
          <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
            <Text style={{ fontSize: 18, fontWeight: '700', color: '#111827', marginBottom: 12 }}>
              Edit brain dump
            </Text>
            <TextInput
              value={content}
              onChangeText={setContent}
              multiline
              maxLength={1000}
              autoFocus
              textAlignVertical="top"
              accessibilityLabel="Brain dump content"
              style={{
                minHeight: 150,
                maxHeight: 280,
                backgroundColor: '#F9FAFB',
                borderColor: '#E5E7EB',
                borderWidth: 1,
                borderRadius: 12,
                padding: 14,
                color: '#111827',
                fontSize: 15,
              }}
            />
            <Text style={{ color: '#9CA3AF', textAlign: 'right', fontSize: 12, marginTop: 6 }}>
              {content.length}/1000
            </Text>
            {error && (
              <Text accessibilityRole="alert" style={{ color: '#DC2626', marginTop: 8 }}>
                {error}
              </Text>
            )}
            <View style={{ flexDirection: 'row', gap: 10, marginTop: 16 }}>
              <TouchableOpacity
                onPress={onClose}
                disabled={saving}
                style={{
                  flex: 1,
                  borderRadius: 10,
                  padding: 13,
                  alignItems: 'center',
                  backgroundColor: '#F3F4F6',
                }}
              >
                <Text style={{ color: '#374151', fontWeight: '600' }}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity
                onPress={handleSave}
                disabled={saving || !content.trim()}
                style={{
                  flex: 1,
                  borderRadius: 10,
                  padding: 13,
                  alignItems: 'center',
                  backgroundColor: '#4F46E5',
                  opacity: saving || !content.trim() ? 0.6 : 1,
                }}
              >
                {saving ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text style={{ color: '#fff', fontWeight: '600' }}>Save changes</Text>
                )}
              </TouchableOpacity>
            </View>
          </KeyboardAvoidingView>
        </Pressable>
      </Pressable>
    </Modal>
  );
}
