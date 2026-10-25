import { Text, TouchableOpacity, View } from 'react-native';
import ElvynMascot from '../ElvynMascot';
import FormattedText from './FormattedText';
import MemorySources from './MemorySources';
import PendingActionCard from './PendingActionCard';
import type { ChatMessage } from './chatTypes';
import { useColors } from '../../theme/colors';

type Props = {
  message: ChatMessage;
  showAvatar: boolean;
  busy: boolean;
  onConfirm: (message: ChatMessage) => void;
  onReject: (message: ChatMessage) => void;
  onRetry: (message: ChatMessage) => void;
};

export default function ChatBubble({ message, showAvatar, busy, onConfirm, onReject, onRetry }: Props) {
  const colors = useColors();
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <View style={{ alignSelf: 'flex-end', maxWidth: '84%', marginBottom: 10 }}>
        <View
          style={{
            backgroundColor: colors.primary,
            borderRadius: 18,
            borderBottomRightRadius: 6,
            paddingHorizontal: 14,
            paddingVertical: 10,
          }}
        >
          <Text style={{ color: '#FFFFFF', fontSize: 15, lineHeight: 21 }}>{message.text}</Text>
        </View>
        <Text style={{ color: colors.textMuted, fontSize: 11, marginTop: 3, alignSelf: 'flex-end' }}>
          {message.timestamp}
        </Text>
      </View>
    );
  }

  return (
    <View style={{ flexDirection: 'row', alignItems: 'flex-end', marginBottom: 10, maxWidth: '92%' }}>
      <View style={{ width: 34, marginRight: 8, alignItems: 'center' }}>
        {showAvatar && <ElvynMascot variant="supportive" size={30} />}
      </View>
      <View style={{ flexShrink: 1 }}>
        <View
          style={{
            backgroundColor: colors.surface,
            borderWidth: 1,
            borderColor: colors.border,
            borderRadius: 18,
            borderBottomLeftRadius: 6,
            paddingHorizontal: 14,
            paddingVertical: 11,
          }}
        >
          <FormattedText text={message.text} color={colors.text} bulletColor={colors.primary} />
          <MemorySources sources={message.sources} />
          {message.pendingActionId && message.pendingActionSummary ? (
            <PendingActionCard
              summary={message.pendingActionSummary}
              status={message.pendingActionStatus}
              busy={busy}
              onConfirm={() => onConfirm(message)}
              onReject={() => onReject(message)}
            />
          ) : null}
          {message.failed && message.retryText ? (
            <TouchableOpacity
              onPress={() => onRetry(message)}
              disabled={busy}
              accessibilityRole="button"
              style={{
                alignSelf: 'flex-start',
                marginTop: 10,
                backgroundColor: colors.primarySoft,
                borderRadius: 12,
                paddingHorizontal: 14,
                paddingVertical: 8,
              }}
            >
              <Text style={{ color: colors.primary, fontWeight: '700' }}>Try again</Text>
            </TouchableOpacity>
          ) : null}
        </View>
        <Text style={{ color: colors.textMuted, fontSize: 11, marginTop: 3 }}>{message.timestamp}</Text>
      </View>
    </View>
  );
}
