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
import { useColors } from '../../theme/colors';

const SAVE_ERROR = "Couldn't save that. Check your connection and try again.";

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
  const colors = useColors();
  const [content, setContent] = useState(dump?.content ?? '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(false);

  async function handleSave() {
    if (!dump || !content.trim()) return;

    setSaving(true);
    setError(false);
    try {
      onSaved(await updateBrainDump(dump.id, content.trim()));
    } catch (saveError) {
      console.warn('Could not save edited brain dump:', saveError);
      setError(true);
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
        accessibilityRole="button"
        accessibilityLabel="Close edit brain dump"
        style={{ flex: 1, backgroundColor: colors.overlay }}
      >
        <KeyboardAvoidingView
          style={{ flex: 1, justifyContent: 'flex-end' }}
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        >
          <Pressable
            onPress={(event) => event.stopPropagation()}
            style={{
              backgroundColor: colors.surface,
              borderTopLeftRadius: 24,
              borderTopRightRadius: 24,
              borderColor: colors.border,
              borderWidth: 1,
              padding: 20,
              paddingBottom: 24,
            }}
          >
            <Text
              accessibilityRole="header"
              maxFontSizeMultiplier={1.2}
              style={{ fontSize: 16, lineHeight: 22, fontWeight: '600', color: colors.text, marginBottom: 12 }}
            >
              Edit brain dump
            </Text>
            <TextInput
              value={content}
              onChangeText={(text) => {
                setContent(text);
                setError(false);
              }}
              multiline
              maxLength={1000}
              autoFocus
              textAlignVertical="top"
              maxFontSizeMultiplier={1.4}
              accessibilityLabel="Brain dump content"
              style={{
                minHeight: 150,
                maxHeight: 280,
                backgroundColor: colors.background,
                borderColor: colors.border,
                borderWidth: 1,
                borderRadius: 12,
                padding: 14,
                color: colors.text,
                fontSize: 14,
                lineHeight: 20,
              }}
            />
            <Text
              maxFontSizeMultiplier={1.2}
              style={{ color: content.length >= 950 ? colors.danger : colors.textMuted, textAlign: 'right', fontSize: 12, lineHeight: 16, marginTop: 6 }}
            >
              {content.length}/1000
            </Text>
            {error ? (
              <Text
                accessibilityRole="alert"
                maxFontSizeMultiplier={1.4}
                style={{ color: colors.danger, fontSize: 13, lineHeight: 18, marginTop: 8 }}
              >
                {SAVE_ERROR}
              </Text>
            ) : null}
            <View style={{ flexDirection: 'row', gap: 10, marginTop: 16 }}>
              <TouchableOpacity
                onPress={onClose}
                disabled={saving}
                accessibilityRole="button"
                accessibilityLabel="Cancel editing"
                style={{
                  flex: 1,
                  minHeight: 44,
                  borderRadius: 12,
                  alignItems: 'center',
                  justifyContent: 'center',
                  backgroundColor: colors.background,
                  borderColor: colors.border,
                  borderWidth: 1,
                }}
              >
                <Text maxFontSizeMultiplier={1.2} style={{ color: colors.text, fontWeight: '600', fontSize: 14, lineHeight: 20 }}>
                  Cancel
                </Text>
              </TouchableOpacity>
              <TouchableOpacity
                onPress={() => void handleSave()}
                disabled={saving || !content.trim()}
                accessibilityRole="button"
                accessibilityLabel="Save changes"
                style={{
                  flex: 1,
                  minHeight: 44,
                  borderRadius: 12,
                  alignItems: 'center',
                  justifyContent: 'center',
                  backgroundColor: colors.primary,
                  opacity: saving || !content.trim() ? 0.6 : 1,
                }}
              >
                {saving ? (
                  <ActivityIndicator color={colors.surface} />
                ) : (
                  <Text maxFontSizeMultiplier={1.2} style={{ color: colors.surface, fontWeight: '600', fontSize: 14, lineHeight: 20 }}>
                    Save changes
                  </Text>
                )}
              </TouchableOpacity>
            </View>
          </Pressable>
        </KeyboardAvoidingView>
      </Pressable>
    </Modal>
  );
}
