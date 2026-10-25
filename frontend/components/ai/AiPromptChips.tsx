import { Text, TouchableOpacity, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useColors } from '../../theme/colors';

// Worded to match what Elvyn can actually answer from the user's own data.
const CHIPS: { icon: keyof typeof Ionicons.glyphMap; text: string }[] = [
  { icon: 'list-outline', text: "What's on my plate today?" },
  { icon: 'calendar-outline', text: 'Help me plan my day' },
  { icon: 'time-outline', text: 'What have I been putting off?' },
  { icon: 'heart-outline', text: 'How have I been feeling lately?' },
];

export default function AIPromptChips({ onSelect, disabled }: { onSelect: (text: string) => void; disabled?: boolean }) {
  const colors = useColors();
  return (
    <View style={{ flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between' }}>
      {CHIPS.map((chip) => (
        <TouchableOpacity
          key={chip.text}
          disabled={disabled}
          onPress={() => onSelect(chip.text)}
          accessibilityRole="button"
          style={{
            width: '48.5%',
            backgroundColor: colors.surface,
            borderWidth: 1,
            borderColor: colors.border,
            borderRadius: 16,
            padding: 12,
            marginBottom: 10,
            minHeight: 78,
            opacity: disabled ? 0.6 : 1,
          }}
        >
          <View
            style={{
              width: 32,
              height: 32,
              borderRadius: 10,
              backgroundColor: colors.primarySoft,
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: 8,
            }}
          >
            <Ionicons name={chip.icon} size={18} color={colors.primary} />
          </View>
          <Text style={{ color: colors.text, fontSize: 13, fontWeight: '600' }}>{chip.text}</Text>
        </TouchableOpacity>
      ))}
    </View>
  );
}
