import { Modal, View, Text, TouchableOpacity, Pressable } from 'react-native';
import { useColors } from '../../theme/colors';

export type TaskActionKey = 'done' | 'not_now' | 'reschedule' | 'edit' | 'cancel';

interface Props {
  visible: boolean;
  onDismiss: () => void;
  onSelect: (key: TaskActionKey) => void;
}

const ACTIONS: { key: TaskActionKey; icon: string; label: string; hint: string; destructive?: boolean }[] = [
  { key: 'done', icon: '✓', label: 'Mark as done', hint: 'Finished with this one' },
  { key: 'not_now', icon: '🕒', label: 'Not now', hint: 'Move it to later or tomorrow' },
  { key: 'reschedule', icon: '📅', label: 'Reschedule', hint: 'Pick a new day and time' },
  { key: 'edit', icon: '✏️', label: 'Edit task', hint: 'Change title, notes or priority' },
  { key: 'cancel', icon: '✕', label: 'Cancel task', hint: 'Remove it from your list', destructive: true },
];

export default function TaskActionSheet({ visible, onDismiss, onSelect }: Props) {
  const colors = useColors();
  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onDismiss}>
      <Pressable style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.4)' }} onPress={onDismiss}>
        <Pressable
          onPress={(e) => e.stopPropagation()}
          style={{
            marginTop: 'auto',
            backgroundColor: colors.surface,
            borderTopLeftRadius: 24,
            borderTopRightRadius: 24,
            padding: 16,
            paddingBottom: 28,
          }}
        >
          <Text style={{ textAlign: 'center', fontWeight: '700', fontSize: 16, color: colors.text, marginBottom: 8 }}>
            Task actions
          </Text>
          {ACTIONS.map((a) => (
            <TouchableOpacity
              key={a.key}
              onPress={() => onSelect(a.key)}
              style={{ flexDirection: 'row', alignItems: 'center', paddingVertical: 10 }}
            >
              <View
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: 12,
                  backgroundColor: colors.primarySoft,
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginRight: 14,
                }}
              >
                <Text style={{ fontSize: 18 }}>{a.icon}</Text>
              </View>
              <View style={{ flex: 1 }}>
                <Text style={{ fontSize: 15, fontWeight: '600', color: a.destructive ? colors.danger : colors.text }}>
                  {a.label}
                </Text>
                <Text style={{ fontSize: 12, color: colors.textMuted, marginTop: 1 }}>{a.hint}</Text>
              </View>
            </TouchableOpacity>
          ))}
          <TouchableOpacity
            onPress={onDismiss}
            style={{ marginTop: 8, paddingVertical: 14, borderRadius: 12, backgroundColor: colors.background, alignItems: 'center' }}
          >
            <Text style={{ color: colors.text, fontWeight: '600' }}>Close</Text>
          </TouchableOpacity>
        </Pressable>
      </Pressable>
    </Modal>
  );
}
