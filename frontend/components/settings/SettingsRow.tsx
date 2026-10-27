import type { ReactNode } from 'react';
import { ActivityIndicator, Switch, Text, TouchableOpacity, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useColors } from '../../theme/colors';

type RowProps = {
  icon: keyof typeof Ionicons.glyphMap;
  title: string;
  subtitle?: string;
  /** Short text on the right, e.g. "On". */
  value?: string;
  onPress?: () => void;
  /** Renders a switch instead of a chevron. */
  switchValue?: boolean;
  onSwitch?: (next: boolean) => void;
  switchDisabled?: boolean;
  loading?: boolean;
  danger?: boolean;
  last?: boolean;
};

export function SettingsRow({
  icon, title, subtitle, value, onPress, switchValue, onSwitch, switchDisabled, loading, danger, last,
}: RowProps) {
  const colors = useColors();
  const tint = danger ? colors.danger : colors.primary;
  const isSwitch = switchValue !== undefined;
  const tappable = !!onPress && !isSwitch;

  const body = (
    <View
      style={{
        flexDirection: 'row', alignItems: 'center', paddingVertical: 12, paddingHorizontal: 14,
        borderBottomWidth: last ? 0 : 1, borderBottomColor: colors.border,
      }}
    >
      <View
        style={{
          width: 36, height: 36, borderRadius: 10, alignItems: 'center', justifyContent: 'center',
          backgroundColor: tint + '22', marginRight: 12,
        }}
      >
        <Ionicons name={icon} size={19} color={tint} />
      </View>
      <View style={{ flex: 1, paddingRight: 8 }}>
        <Text style={{ color: danger ? colors.danger : colors.text, fontSize: 15, fontWeight: '600' }}>{title}</Text>
        {subtitle ? (
          <Text style={{ color: colors.textMuted, fontSize: 12.5, marginTop: 2, lineHeight: 17 }}>{subtitle}</Text>
        ) : null}
      </View>
      {loading ? (
        <ActivityIndicator size="small" color={colors.primary} />
      ) : isSwitch ? (
        <Switch
          value={switchValue}
          onValueChange={onSwitch}
          disabled={switchDisabled}
          trackColor={{ false: colors.border, true: colors.primary }}
          thumbColor="#FFFFFF"
        />
      ) : (
        <>
          {value ? <Text style={{ color: colors.textMuted, fontSize: 13, marginRight: 6 }}>{value}</Text> : null}
          {tappable ? <Ionicons name="chevron-forward" size={18} color={colors.textMuted} /> : null}
        </>
      )}
    </View>
  );

  if (!tappable) return body;
  return (
    <TouchableOpacity onPress={onPress} disabled={loading} accessibilityRole="button" activeOpacity={0.7}>
      {body}
    </TouchableOpacity>
  );
}

type GroupProps = { label?: string; footer?: string; children: ReactNode };

export function SettingsGroup({ label, footer, children }: GroupProps) {
  const colors = useColors();
  return (
    <View style={{ marginTop: 22 }}>
      {label ? (
        <Text
          style={{
            color: colors.textMuted, fontSize: 12, fontWeight: '700', letterSpacing: 0.8,
            marginBottom: 8, marginLeft: 4,
          }}
        >
          {label.toUpperCase()}
        </Text>
      ) : null}
      <View
        style={{
          backgroundColor: colors.surface, borderRadius: 16, borderWidth: 1,
          borderColor: colors.border, overflow: 'hidden',
        }}
      >
        {children}
      </View>
      {footer ? (
        <Text style={{ color: colors.textMuted, fontSize: 12.5, lineHeight: 18, marginTop: 8, marginHorizontal: 4 }}>
          {footer}
        </Text>
      ) : null}
    </View>
  );
}
