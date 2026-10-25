import { ActivityIndicator, Text, TouchableOpacity, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useColors } from '../../theme/colors';

type Props = {
  summary: string;
  status?: string; // 'pending' | resolved states from the API
  busy: boolean;
  onConfirm: () => void;
  onReject: () => void;
};

const RESOLVED_LABEL: Record<string, string> = {
  created: 'Added',
  updated: 'Updated',
  cancelled: 'Cancelled',
  rejected: 'Not changed',
  expired: 'Expired — ask me again',
  stale: 'Out of date — ask me again',
  resolved: 'Done',
};

export default function PendingActionCard({ summary, status, busy, onConfirm, onReject }: Props) {
  const colors = useColors();
  const pending = status === 'pending';
  return (
    <View
      style={{
        marginTop: 10,
        backgroundColor: colors.warmSurface,
        borderColor: colors.warmBorder,
        borderWidth: 1,
        borderRadius: 14,
        padding: 12,
      }}
    >
      <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 6 }}>
        <Ionicons name="shield-checkmark-outline" size={16} color={colors.accent} />
        <Text style={{ color: colors.textMuted, fontSize: 12, marginLeft: 6, fontWeight: '600' }}>
          Needs your OK
        </Text>
      </View>
      <Text style={{ color: colors.text, fontWeight: '600', fontSize: 14 }}>{summary}</Text>
      {pending ? (
        <View style={{ flexDirection: 'row', marginTop: 12 }}>
          <TouchableOpacity
            disabled={busy}
            onPress={onConfirm}
            accessibilityRole="button"
            style={{
              flex: 1,
              backgroundColor: colors.primary,
              borderRadius: 10,
              paddingVertical: 10,
              alignItems: 'center',
              marginRight: 8,
              opacity: busy ? 0.6 : 1,
            }}
          >
            {busy ? (
              <ActivityIndicator color="#fff" size="small" />
            ) : (
              <Text style={{ color: '#fff', fontWeight: '700' }}>Confirm</Text>
            )}
          </TouchableOpacity>
          <TouchableOpacity
            disabled={busy}
            onPress={onReject}
            accessibilityRole="button"
            style={{
              flex: 1,
              borderWidth: 1,
              borderColor: colors.border,
              backgroundColor: colors.surface,
              borderRadius: 10,
              paddingVertical: 10,
              alignItems: 'center',
              opacity: busy ? 0.6 : 1,
            }}
          >
            <Text style={{ color: colors.text, fontWeight: '600' }}>No thanks</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <Text style={{ color: colors.textMuted, fontSize: 12, marginTop: 8 }}>
          {RESOLVED_LABEL[status ?? 'resolved'] ?? 'Done'}
        </Text>
      )}
    </View>
  );
}
