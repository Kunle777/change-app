import { ScrollView, Text, TouchableOpacity, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import ElvynMascot from '../ElvynMascot';
import AIPromptChips from './AiPromptChips';
import { greetingFor } from '../../utils/chatFormat';
import { useColors } from '../../theme/colors';

type Props = {
  firstName: string;
  disabled: boolean;
  onPrompt: (text: string) => void;
  onEveningSummary: () => void;
};

export default function ChatEmptyState({ firstName, disabled, onPrompt, onEveningSummary }: Props) {
  const colors = useColors();
  return (
    <ScrollView
      contentContainerStyle={{ padding: 16, paddingBottom: 24 }}
      keyboardShouldPersistTaps="handled"
    >
      <View style={{ alignItems: 'center', marginTop: 8, marginBottom: 18 }}>
        <ElvynMascot variant="supportive" size={96} />
        <Text style={{ color: colors.text, fontSize: 20, fontWeight: '800', marginTop: 10 }}>
          {greetingFor()}
          {firstName ? `, ${firstName}` : ''}
        </Text>
        <Text style={{ color: colors.textMuted, fontSize: 14, marginTop: 4, textAlign: 'center' }}>
          I'm here. What would you like to talk about?
        </Text>
      </View>

      <Text style={{ color: colors.textMuted, fontSize: 12, fontWeight: '700', marginBottom: 8, letterSpacing: 0.5 }}>
        TRY ASKING
      </Text>
      <AIPromptChips onSelect={onPrompt} disabled={disabled} />

      <TouchableOpacity
        onPress={onEveningSummary}
        disabled={disabled}
        accessibilityRole="button"
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          backgroundColor: colors.lavenderSurface,
          borderWidth: 1,
          borderColor: colors.border,
          borderRadius: 16,
          padding: 14,
          marginTop: 2,
          opacity: disabled ? 0.6 : 1,
        }}
      >
        <View
          style={{
            width: 36,
            height: 36,
            borderRadius: 12,
            backgroundColor: colors.primarySoft,
            alignItems: 'center',
            justifyContent: 'center',
            marginRight: 12,
          }}
        >
          <Ionicons name="moon-outline" size={18} color={colors.primary} />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={{ color: colors.text, fontWeight: '700' }}>Evening summary</Text>
          <Text style={{ color: colors.textMuted, fontSize: 12, marginTop: 2 }}>
            A calm look back at your day
          </Text>
        </View>
        <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
      </TouchableOpacity>

      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', marginTop: 20 }}>
        <Ionicons name="lock-closed-outline" size={13} color={colors.textMuted} />
        <Text style={{ color: colors.textMuted, fontSize: 11, marginLeft: 6, flexShrink: 1, textAlign: 'center' }}>
          Elvyn looks at your tasks. Saved entries are used only if Personal memory is on.
        </Text>
      </View>
    </ScrollView>
  );
}
