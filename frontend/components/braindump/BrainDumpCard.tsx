import { View, Text, TouchableOpacity } from 'react-native';
import { BrainDump } from '../../types/brainDump';

export default function BrainDumpCard({ dump, onPress }: { dump: BrainDump; onPress: () => void }) {
  return (
    <TouchableOpacity
      onPress={onPress}
      style={{ backgroundColor: '#fff', borderRadius: 14, padding: 14, marginBottom: 10 }}
    >
      <Text numberOfLines={2} style={{ fontSize: 14 }}>
        {dump.content}
      </Text>
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
    </TouchableOpacity>
  );
}
