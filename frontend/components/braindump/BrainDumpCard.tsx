import { Ionicons } from '@expo/vector-icons';
import { Text, TouchableOpacity, View } from 'react-native';
import { useColors } from '../../theme/colors';
import { BrainDump } from '../../types/brainDump';
import { formatDumpTime } from '../../utils/dumpTime';

export default function BrainDumpCard({
  dump,
  onPress,
  onMorePress,
}: {
  dump: BrainDump;
  onPress: () => void;
  onMorePress: () => void;
}) {
  const colors = useColors();

  return (
    <View
      style={{
        backgroundColor: colors.surface,
        borderRadius: 16,
        borderWidth: 1,
        borderColor: colors.border,
        padding: 12,
        marginBottom: 12,
      }}
    >
      <TouchableOpacity
        onPress={onPress}
        accessibilityRole="button"
        accessibilityLabel={`Open brain dump: ${dump.content}`}
        style={{ flexDirection: 'row', alignItems: 'flex-start' }}
      >
        <View
          style={{
            width: 40,
            height: 40,
            borderRadius: 12,
            backgroundColor: colors.primarySoft,
            alignItems: 'center',
            justifyContent: 'center',
            marginRight: 10,
          }}
        >
          <Ionicons name="document-text-outline" size={19} color={colors.primary} />
        </View>
        <View style={{ flex: 1, minWidth: 0 }}>
          <Text
            numberOfLines={2}
            maxFontSizeMultiplier={1.4}
            style={{ color: colors.text, fontSize: 14, lineHeight: 20 }}
          >
            {dump.content}
          </Text>
          <Text
            maxFontSizeMultiplier={1.2}
            style={{ color: colors.textMuted, fontSize: 12, lineHeight: 16, marginTop: 4 }}
          >
            {formatDumpTime(dump.created_at)}
          </Text>
        </View>
      </TouchableOpacity>

      <View style={{ flexDirection: 'row', justifyContent: 'flex-end', alignItems: 'center', marginTop: 4 }}>
        {dump.is_converted ? (
          <View
            style={{
              flexDirection: 'row',
              alignItems: 'center',
              backgroundColor: colors.successSoft,
              borderRadius: 10,
              paddingHorizontal: 9,
              minHeight: 30,
            }}
          >
            <Ionicons name="checkmark-circle-outline" size={14} color={colors.success} />
            <Text
              maxFontSizeMultiplier={1.2}
              style={{ color: colors.success, fontSize: 12, lineHeight: 16, fontWeight: '600', marginLeft: 4 }}
            >
              Converted
            </Text>
          </View>
        ) : dump.possible_task ? (
          <View
            style={{
              flexDirection: 'row',
              alignItems: 'center',
              backgroundColor: colors.primarySoft,
              borderRadius: 10,
              paddingHorizontal: 9,
              minHeight: 30,
            }}
          >
            <Ionicons name="sparkles-outline" size={14} color={colors.primary} />
            <Text
              maxFontSizeMultiplier={1.2}
              style={{ color: colors.primary, fontSize: 12, lineHeight: 16, fontWeight: '600', marginLeft: 4 }}
            >
              Possible task
            </Text>
          </View>
        ) : null}
        <TouchableOpacity
          onPress={onMorePress}
          accessibilityRole="button"
          accessibilityLabel="Brain dump options"
          style={{ width: 44, height: 44, alignItems: 'center', justifyContent: 'center', marginLeft: 4 }}
        >
          <Text
            maxFontSizeMultiplier={1.2}
            style={{ color: colors.textMuted, fontSize: 24, lineHeight: 28 }}
          >
            ⋯
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}
