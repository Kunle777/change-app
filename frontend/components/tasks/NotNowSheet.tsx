import { Modal, View, Text, TouchableOpacity, Pressable } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useColors } from '../../theme/colors';

export type NotNowOption = 'later_today' | 'tomorrow';

interface Props {
  visible: boolean;
  onClose: () => void;
  onPick: (option: NotNowOption) => void;
}

function formatTime(date: Date) {
  return date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
}

export default function NotNowSheet({ visible, onClose, onPick }: Props) {
  const colors = useColors();
  const now = new Date();
  const later = new Date(now.getTime() + 3 * 60 * 60 * 1000);
  const laterIsToday = later.toDateString() === now.toDateString();
  const options: { key: NotNowOption; label: string; hint: string }[] = [
    ...(laterIsToday
      ? [{ key: 'later_today' as const, label: 'Later today', hint: `Today, ${formatTime(later)}` }]
      : []),
    { key: 'tomorrow', label: 'Tomorrow', hint: 'Tomorrow, 9:00 AM' },
  ];

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.45)' }} onPress={onClose}>
        <Pressable
          onPress={(event) => event.stopPropagation()}
          style={{ marginTop: 'auto', backgroundColor: colors.surface, borderTopLeftRadius: 28, borderTopRightRadius: 28, padding: 20, paddingBottom: 28 }}
        >
          <View style={{ flexDirection: 'row', alignItems: 'center' }}>
            <Ionicons name="time-outline" size={24} color={colors.primary} />
            <Text style={{ color: colors.text, fontSize: 18, fontWeight: '800', marginLeft: 10 }}>Not now</Text>
          </View>
          <Text style={{ color: colors.textMuted, fontSize: 13, marginTop: 4, marginBottom: 14 }}>
            When should Elvyn remind you?
          </Text>

          {options.map((option) => (
            <TouchableOpacity
              key={option.key}
              onPress={() => {
                onClose();
                onPick(option.key);
              }}
              style={{ borderWidth: 1, borderColor: colors.border, borderRadius: 16, padding: 14, marginBottom: 10 }}
            >
              <Text style={{ color: colors.text, fontWeight: '600', fontSize: 15 }}>{option.label}</Text>
              <Text style={{ color: colors.textMuted, fontSize: 12, marginTop: 2 }}>{option.hint}</Text>
            </TouchableOpacity>
          ))}

          <Text style={{ color: colors.textMuted, fontSize: 12, marginBottom: 12 }}>
            Want a specific date or time? Use Reschedule instead.
          </Text>
          <TouchableOpacity onPress={onClose} style={{ backgroundColor: colors.primarySoft, borderRadius: 14, paddingVertical: 14, alignItems: 'center' }}>
            <Text style={{ color: colors.primary, fontWeight: '700' }}>Cancel</Text>
          </TouchableOpacity>
        </Pressable>
      </Pressable>
    </Modal>
  );
}
