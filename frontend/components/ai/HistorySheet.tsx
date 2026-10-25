import { useMemo, useState } from 'react';
import { ActivityIndicator, FlatList, Modal, Pressable, Text, TouchableOpacity, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import ElvynMascot from '../ElvynMascot';
import type { ChatConversation } from '../../services/ai';
import { bucketFor, relativeLabel, type HistoryBucket } from '../../utils/chatFormat';
import { useColors } from '../../theme/colors';

type Filter = 'all' | HistoryBucket;
const FILTERS: { key: Filter; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'today', label: 'Today' },
  { key: 'week', label: 'This week' },
  { key: 'older', label: 'Older' },
];

type Props = {
  visible: boolean;
  conversations: ChatConversation[];
  activeId: string | null;
  loading: boolean;
  error: string | null;
  onClose: () => void;
  onSelect: (id: string) => void;
  onNewChat: () => void;
  onRetry: () => void;
};

export default function HistorySheet({
  visible,
  conversations,
  activeId,
  loading,
  error,
  onClose,
  onSelect,
  onNewChat,
  onRetry,
}: Props) {
  const colors = useColors();
  const [filter, setFilter] = useState<Filter>('all');
  const rows = useMemo(
    () => (filter === 'all' ? conversations : conversations.filter((c) => bucketFor(c.updated_at) === filter)),
    [conversations, filter],
  );

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.45)' }} onPress={onClose}>
        <Pressable
          onPress={(e) => e.stopPropagation()}
          style={{
            marginTop: 'auto',
            height: '78%',
            backgroundColor: colors.background,
            borderTopLeftRadius: 24,
            borderTopRightRadius: 24,
            padding: 18,
          }}
        >
          <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <Text style={{ color: colors.text, fontSize: 18, fontWeight: '800' }}>Conversations</Text>
            <TouchableOpacity onPress={onClose} accessibilityLabel="Close" hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}>
              <Ionicons name="close" size={22} color={colors.textMuted} />
            </TouchableOpacity>
          </View>

          <View style={{ flexDirection: 'row', marginBottom: 12 }}>
            {FILTERS.map((f) => (
              <TouchableOpacity
                key={f.key}
                onPress={() => setFilter(f.key)}
                style={{
                  paddingHorizontal: 14,
                  paddingVertical: 7,
                  borderRadius: 16,
                  marginRight: 8,
                  backgroundColor: filter === f.key ? colors.primary : colors.surface,
                  borderWidth: 1,
                  borderColor: filter === f.key ? colors.primary : colors.border,
                }}
              >
                <Text style={{ color: filter === f.key ? '#fff' : colors.text, fontSize: 12, fontWeight: '600' }}>
                  {f.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          {loading ? (
            <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
              <ActivityIndicator color={colors.primary} />
            </View>
          ) : error ? (
            <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', padding: 20 }}>
              <Text style={{ color: colors.text, textAlign: 'center', marginBottom: 12 }}>{error}</Text>
              <TouchableOpacity
                onPress={onRetry}
                style={{ backgroundColor: colors.primarySoft, borderRadius: 12, paddingHorizontal: 18, paddingVertical: 10 }}
              >
                <Text style={{ color: colors.primary, fontWeight: '700' }}>Try again</Text>
              </TouchableOpacity>
            </View>
          ) : conversations.length === 0 ? (
            <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', padding: 20 }}>
              <ElvynMascot variant="neutral" size={84} />
              <Text style={{ color: colors.text, fontWeight: '800', fontSize: 16, marginTop: 12 }}>No conversations yet</Text>
              <Text style={{ color: colors.textMuted, textAlign: 'center', marginTop: 4 }}>
                Start a chat with Elvyn and it will show up here.
              </Text>
            </View>
          ) : (
            <FlatList
              data={rows}
              keyExtractor={(item) => item.id}
              ListEmptyComponent={
                <Text style={{ color: colors.textMuted, textAlign: 'center', marginTop: 30 }}>
                  Nothing in this range.
                </Text>
              }
              renderItem={({ item }) => {
                const active = item.id === activeId;
                return (
                  <TouchableOpacity
                    onPress={() => onSelect(item.id)}
                    style={{
                      flexDirection: 'row',
                      alignItems: 'center',
                      backgroundColor: active ? colors.primarySoft : colors.surface,
                      borderWidth: 1,
                      borderColor: active ? colors.primary : colors.border,
                      borderRadius: 16,
                      padding: 12,
                      marginBottom: 8,
                    }}
                  >
                    <View
                      style={{
                        width: 38,
                        height: 38,
                        borderRadius: 12,
                        backgroundColor: colors.primarySoft,
                        alignItems: 'center',
                        justifyContent: 'center',
                        marginRight: 12,
                      }}
                    >
                      <Ionicons name="chatbubble-ellipses-outline" size={18} color={colors.primary} />
                    </View>
                    <Text style={{ flex: 1, color: colors.text, fontWeight: '600' }} numberOfLines={2}>
                      {item.title}
                    </Text>
                    <Text style={{ color: colors.textMuted, fontSize: 11, marginLeft: 8 }}>
                      {relativeLabel(item.updated_at)}
                    </Text>
                  </TouchableOpacity>
                );
              }}
            />
          )}

          <TouchableOpacity
            onPress={onNewChat}
            accessibilityRole="button"
            style={{ backgroundColor: colors.primary, borderRadius: 14, paddingVertical: 14, alignItems: 'center', marginTop: 8 }}
          >
            <Text style={{ color: '#fff', fontWeight: '800' }}>+ New chat</Text>
          </TouchableOpacity>
        </Pressable>
      </Pressable>
    </Modal>
  );
}
