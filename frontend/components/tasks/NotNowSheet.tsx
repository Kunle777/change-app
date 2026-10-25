import { Modal, Pressable, Text, TouchableOpacity, View } from 'react-native';
import { useColors } from '../../theme/colors';

export type NotNowOption = 'later_today' | 'tomorrow';

interface Props {
  visible: boolean;
  onClose: () => void;
  onPick: (option: NotNowOption) => void;
}

function formatTime(d: Date) {
  return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
}

export default function NotNowSheet({ visible, onClose, onPick }: Props) {
  const colors = useColors();
  const later = new Date(Date.now() + 3 * 60 * 60 * 1000);
  const sameDay = later.toDateString() === new Date().toDateString();

  const options: { key: NotNowOption; label: string; hint: string }[] = [
    {
      key: 'later_today',
      label: 'Later today',
      hint: sameDay ? `Remind me at ${formatTime(later)}` : `Remind me ${formatTime(later)} (tomorrow)`,
    },
    { key: 'tomorrow', label: 'Tomorrow', hint: 'Remind me at 9:00 AM' },
  ];

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.4)' }} onPress={onClose}>
        <Pressable
          onPress={(e) => e.stopPropagation()}
          style={{
            marginTop: 'auto',
            backgroundColor: colors.surface,
            borderTopLeftRadius: 24,
            borderTopRightRadius: 24,
            padding: 20,
            paddingBottom: 28,
          }}
        >
          <Text style={{ fontWeight: '700', fontSize: 17, color: colors.text }}>Not now</Text>
          <Text style={{ color: colors.textMuted, fontSize: 13, marginTop: 2, marginBottom: 12 }}>
            That's okay. When should Elvyn bring it back?
          </Text>
          {options.map((o) => (
            <TouchableOpacity
              key={o.key}
              onPress={() => {
                onClose();
                onPick(o.key);
              }}
              style={{
                padding: 14,
                borderRadius: 14,
                borderWidth: 1,
                borderColor: colors.border,
                marginBottom: 10,
              }}
            >
              <Text style={{ color: colors.text, fontWeight: '600', fontSize: 15 }}>{o.label}</Text>
              <Text style={{ color: colors.textMuted, fontSize: 12, marginTop: 2 }}>{o.hint}</Text>
            </TouchableOpacity>
          ))}
          <TouchableOpacity onPress={onClose} style={{ alignItems: 'center', padding: 8 }}>
            <Text style={{ color: colors.textMuted }}>Cancel</Text>
          </TouchableOpacity>
        </Pressable>
      </Pressable>
    </Modal>
  );
}
