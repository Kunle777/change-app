import { View, Text, TouchableOpacity } from 'react-native';
import { BrainDump } from '../../types/brainDump';

export default function BrainDumpCard({
  dump,
  onPress,
  onMorePress,
}: {
  dump: BrainDump;
  onPress: () => void;
  onMorePress: () => void;
}) {
  return (
    <View
      style={{
        backgroundColor: '#fff',
        borderRadius: 14,
        padding: 14,
        marginBottom: 10,
      }}
    >
      <View style={{ flexDirection: 'row', alignItems: 'flex-start', gap: 8 }}>
        <TouchableOpacity
          onPress={onPress}
          accessibilityRole="button"
          accessibilityLabel="Open brain dump"
          style={{ flex: 1 }}
        >
          <Text numberOfLines={2} style={{ fontSize: 14 }}>
            {dump.content}
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          onPress={onMorePress}
          accessibilityRole="button"
          accessibilityLabel="Brain dump options"
          hitSlop={8}
          style={{ paddingHorizontal: 6, marginTop: -5 }}
        >
          <Text style={{ fontSize: 24, lineHeight: 26, color: '#6B7280' }}>⋯</Text>
        </TouchableOpacity>
      </View>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: 8 }}>
        <Text style={{ fontSize: 11, color: '#999' }}>
          {new Date(dump.created_at).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}
        </Text>
        {dump.is_converted ? (
          <Text style={{ fontSize: 11, color: '#10B981' }}>✓ Converted</Text>
        ) : dump.possible_task ? (
          <Text style={{ fontSize: 11, color: '#4F46E5' }}>✨ Possible task</Text>
        ) : null}
      </View>
    </View>
  );
}
