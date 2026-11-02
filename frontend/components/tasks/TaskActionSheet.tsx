import { Modal, View, Text, TouchableOpacity, Pressable } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useColors } from '../../theme/colors';

export type TaskActionKey = 'done' | 'not_now' | 'reschedule' | 'edit' | 'cancel';

interface Props {
  visible: boolean;
  onDismiss: () => void;
  onSelect: (key: TaskActionKey) => void;
}

const ACTIONS: {
  key: TaskActionKey;
  icon: React.ComponentProps<typeof Ionicons>['name'];
  label: string;
  hint: string;
  tint: string;
}[] = [
  { key: 'done', icon: 'checkmark-circle', label: 'Mark as done', hint: 'Complete this task', tint: '#10B981' },
  { key: 'not_now', icon: 'time-outline', label: 'Not now', hint: 'Come back to it later', tint: '#4F46E5' },
  { key: 'reschedule', icon: 'calendar-outline', label: 'Reschedule', hint: 'Change date or time', tint: '#4F46E5' },
  { key: 'edit', icon: 'create-outline', label: 'Edit task', hint: 'Update details', tint: '#EC4899' },
  { key: 'cancel', icon: 'trash-outline', label: 'Cancel task', hint: "I'm not doing this one", tint: '#EF4444' },
];

export default function TaskActionSheet({ visible, onDismiss, onSelect }: Props) {
  const colors = useColors();

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onDismiss}>
      <Pressable style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.45)' }} onPress={onDismiss}>
        <Pressable
          onPress={(event) => event.stopPropagation()}
          style={{
            marginTop: 'auto',
            backgroundColor: colors.surface,
            borderTopLeftRadius: 28,
            borderTopRightRadius: 28,
            paddingHorizontal: 16,
            paddingTop: 10,
            paddingBottom: 24,
          }}
        >
          <View style={{ alignSelf: 'center', width: 40, height: 4, borderRadius: 2, backgroundColor: colors.border, marginBottom: 14 }} />
          <Text style={{ color: colors.text, fontSize: 18, fontWeight: '800', marginBottom: 8, marginLeft: 4 }}>Task actions</Text>

          {ACTIONS.map((action) => (
            <TouchableOpacity
              key={action.key}
              onPress={() => onSelect(action.key)}
              style={{ flexDirection: 'row', alignItems: 'center', paddingVertical: 10 }}
            >
              <View style={{ width: 44, height: 44, borderRadius: 22, backgroundColor: `${action.tint}1F`, alignItems: 'center', justifyContent: 'center' }}>
                <Ionicons name={action.icon} size={22} color={action.tint} />
              </View>
              <View style={{ flex: 1, marginLeft: 14 }}>
                <Text style={{ color: colors.text, fontSize: 15, fontWeight: '600' }}>{action.label}</Text>
                <Text style={{ color: colors.textMuted, fontSize: 12, marginTop: 1 }}>{action.hint}</Text>
              </View>
              <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
            </TouchableOpacity>
          ))}

          <TouchableOpacity
            onPress={onDismiss}
            style={{ marginTop: 10, backgroundColor: colors.primarySoft, borderRadius: 14, paddingVertical: 14, alignItems: 'center' }}
          >
            <Text style={{ color: colors.primary, fontWeight: '700' }}>Close</Text>
          </TouchableOpacity>
        </Pressable>
      </Pressable>
    </Modal>
  );
}
