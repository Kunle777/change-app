import { ActivityIndicator, Text, TouchableOpacity, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import type { ReactNode } from 'react';
import { useColors } from '../../theme/colors';

type Props = { label: string; onPress: () => void; loading?: boolean; disabled?: boolean; leading?: ReactNode };

export function PrimaryButton({ label, onPress, loading, disabled }: Props) {
  const colors = useColors();
  const off = loading || disabled;
  return (
    <TouchableOpacity
      onPress={onPress}
      disabled={off}
      accessibilityRole="button"
      style={{
        backgroundColor: colors.primary, borderRadius: 14, minHeight: 54,
        flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
        opacity: off ? 0.6 : 1,
      }}
    >
      {loading ? <ActivityIndicator color="#fff" /> : (
        <>
          <Text style={{ color: '#fff', fontWeight: '700', fontSize: 16 }}>{label}</Text>
          <Ionicons name="arrow-forward" size={18} color="#fff" style={{ marginLeft: 8 }} />
        </>
      )}
    </TouchableOpacity>
  );
}

export function SecondaryButton({ label, onPress, loading, disabled, leading }: Props) {
  const colors = useColors();
  const off = loading || disabled;
  return (
    <TouchableOpacity
      onPress={onPress}
      disabled={off}
      accessibilityRole="button"
      style={{
        backgroundColor: colors.surface, borderColor: colors.border, borderWidth: 1,
        borderRadius: 14, minHeight: 54, flexDirection: 'row',
        alignItems: 'center', justifyContent: 'center', opacity: off ? 0.6 : 1,
      }}
    >
      {loading ? <ActivityIndicator color={colors.primary} /> : (
        <>
          {leading ? <View style={{ marginRight: 10 }}>{leading}</View> : null}
          <Text style={{ color: colors.text, fontWeight: '600', fontSize: 15 }}>{label}</Text>
        </>
      )}
    </TouchableOpacity>
  );
}