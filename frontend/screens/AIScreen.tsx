import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Modal,
  Pressable,
} from 'react-native';
import { KeyboardAvoidingView as RNKCKeyboardAvoidingView } from 'react-native-keyboard-controller';
import { SafeAreaView } from 'react-native-safe-area-context';
import {
  sendChatMessage,
  getEveningSummary,
  getChatConversations,
  getChatConversation,
  getPendingChatActions,
  confirmChatAction,
  rejectChatAction,
} from '../services/ai';
import type { ChatConversation, PendingChatAction } from '../services/ai';

type Message = {
  id: string;
  role: 'user' | 'ai';
  text: string;
  timestamp: string;
  pendingActionId?: string;
  pendingActionSummary?: string;
  pendingActionStatus?: string;
};

export default function AIScreen() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<ChatConversation[]>([]);
  const [historyVisible, setHistoryVisible] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const flatListRef = useRef<FlatList>(null);

  useEffect(() => {
    if (messages.length > 0) {
      flatListRef.current?.scrollToEnd({ animated: true });
    }
  }, [messages, sending]);

  const addMessage = (
    role: 'user' | 'ai',
    text: string,
    pendingAction?: { id: string; summary: string },
  ) => {
    const newMessage: Message = {
      id: Date.now().toString() + role,
      role,
      text,
      timestamp: new Date().toLocaleTimeString(),
      pendingActionId: pendingAction?.id,
      pendingActionSummary: pendingAction?.summary,
      pendingActionStatus: pendingAction ? 'pending' : undefined,
    };
    setMessages((prev) => [...prev, newMessage]);
  };

  const openHistory = async () => {
    setHistoryVisible(true);
    setLoadingHistory(true);
    try {
      setConversations(await getChatConversations());
    } catch (err: any) {
      addMessage('ai', `⚠️ ${err.message}`);
    } finally {
      setLoadingHistory(false);
    }
  };

  const selectConversation = async (id: string) => {
    setLoadingHistory(true);
    try {
      const detail = await getChatConversation(id);
      const pendingActions = await getPendingChatActions(id);
      const pendingById = new Map<string, PendingChatAction>(
        pendingActions.map((action) => [action.id, action]),
      );
      setConversationId(detail.id);
      setMessages(
        detail.messages.flatMap((turn) => [
          {
            id: `${turn.id}-user`,
            role: 'user' as const,
            text: turn.question,
            timestamp: new Date(turn.created_at).toLocaleTimeString(),
          },
          {
            id: `${turn.id}-ai`,
            role: 'ai' as const,
            text: turn.response,
            timestamp: new Date(turn.created_at).toLocaleTimeString(),
            pendingActionId: turn.pending_action_id ?? undefined,
            pendingActionSummary: turn.pending_action_id
              ? pendingById.get(turn.pending_action_id)?.summary
              : undefined,
            pendingActionStatus: turn.pending_action_id
              ? pendingById.has(turn.pending_action_id)
                ? 'pending'
                : 'resolved'
              : undefined,
          },
        ]),
      );
      setHistoryVisible(false);
    } catch (err: any) {
      addMessage('ai', `⚠️ ${err.message}`);
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || sending) return;
    const userText = input.trim();
    addMessage('user', userText);
    setInput('');
    setSending(true);
    try {
      const result = await sendChatMessage(userText, conversationId);
      setConversationId(result.conversation_id ?? conversationId);
      addMessage(
        'ai',
        result.message,
        result.pending_action_id
          ? { id: result.pending_action_id, summary: result.pending_action_summary }
          : undefined,
      );
    } catch (err: any) {
      addMessage('ai', `⚠️ ${err.message}`);
    } finally {
      setSending(false);
    }
  };

  const decidePendingAction = async (messageId: string, actionId: string, confirm: boolean) => {
    if (sending) return;
    setSending(true);
    try {
      const result = confirm
        ? await confirmChatAction(actionId)
        : await rejectChatAction(actionId);
      setMessages((current) =>
        current.map((message) =>
          message.id === messageId
            ? { ...message, pendingActionStatus: result.status }
            : message,
        ),
      );
      if (result.status === 'updated' || result.status === 'cancelled') {
        addMessage(
          'ai',
          result.status === 'cancelled'
            ? 'Confirmed. The task was cancelled.'
            : 'Confirmed. The task has been updated.',
        );
      } else if (result.status === 'rejected') {
        addMessage('ai', 'No change was made.');
      } else {
        addMessage('ai', result.reason || 'This action could not be completed.');
      }
    } catch (err: any) {
      addMessage('ai', `⚠️ ${err.message}`);
    } finally {
      setSending(false);
    }
  };

  const handleEveningSummary = async () => {
    if (sending) return;
    setSending(true);
    try {
      const result = await getEveningSummary();
      addMessage('ai', result.message);
    } catch (err: any) {
      addMessage('ai', `⚠️ ${err.message}`);
    } finally {
      setSending(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <RNKCKeyboardAvoidingView
        style={styles.container}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 100 : 80}
      >
        <View style={styles.conversationActions}>
          <TouchableOpacity onPress={openHistory} disabled={sending}>
            <Text style={styles.conversationActionText}>History</Text>
          </TouchableOpacity>
        </View>
        {messages.length === 0 && (
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyText}>
              Ask anything — your tasks, goals, or just how you're doing.
            </Text>
          </View>
        )}
        <FlatList
          ref={flatListRef}
          data={messages}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.list}
          onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: true })}
          renderItem={({ item }) => {
            const isUser = item.role === 'user';
            return (
              <View style={[styles.bubbleContainer, isUser ? styles.userAlign : styles.aiAlign]}>
                <View style={[styles.bubble, isUser ? styles.userBubble : styles.aiBubble]}>
                  <Text style={isUser ? styles.userText : styles.aiText}>{item.text}</Text>
                  <Text
                    style={[styles.timestamp, isUser ? styles.userTimestamp : styles.aiTimestamp]}
                  >
                    {item.timestamp}
                  </Text>
                  {item.pendingActionId && item.pendingActionSummary && (
                    <View style={styles.pendingActionBox}>
                      <Text style={styles.pendingActionSummary}>{item.pendingActionSummary}</Text>
                      {item.pendingActionStatus === 'pending' ? (
                        <View style={styles.pendingActionButtons}>
                          <Pressable
                            disabled={sending}
                            onPress={() =>
                              decidePendingAction(item.id, item.pendingActionId!, true)
                            }
                          >
                            <Text style={styles.confirmActionText}>Confirm</Text>
                          </Pressable>
                          <Pressable
                            disabled={sending}
                            onPress={() =>
                              decidePendingAction(item.id, item.pendingActionId!, false)
                            }
                          >
                            <Text style={styles.rejectActionText}>Reject</Text>
                          </Pressable>
                        </View>
                      ) : (
                        <Text style={styles.pendingActionStatus}>{item.pendingActionStatus}</Text>
                      )}
                    </View>
                  )}
                </View>
              </View>
            );
          }}
        />

        {sending && (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="small" color="#4A90E2" />
            <Text style={styles.loadingText}>Ai is thinking...</Text>
          </View>
        )}

        <TouchableOpacity
          style={[styles.summaryButton, sending && styles.disabledSummaryButton]}
          onPress={handleEveningSummary}
          disabled={sending}
        >
          <Text style={styles.summaryButtonText}>Get evening summary</Text>
        </TouchableOpacity>

        {/* Input Bar */}
        <View style={styles.inputRow}>
          <TextInput
            style={styles.input}
            value={input}
            onChangeText={setInput}
            placeholder="Ask something..."
            placeholderTextColor="#888"
            multiline
            maxLength={1000}
          />
          <TouchableOpacity
            style={[styles.sendButton, (!input.trim() || sending) && styles.disabledSendButton]}
            onPress={handleSend}
            disabled={sending}
          >
            <Text style={styles.sendText}>Send</Text>
          </TouchableOpacity>
        </View>
        <Modal
          visible={historyVisible}
          transparent
          animationType="slide"
          onRequestClose={() => setHistoryVisible(false)}
        >
          <View style={styles.modalBackdrop}>
            <View style={styles.historyPanel}>
              <View style={styles.historyHeader}>
                <Text style={styles.historyTitle}>Conversation history</Text>
                <Pressable onPress={() => setHistoryVisible(false)}>
                  <Text style={styles.conversationActionText}>Close</Text>
                </Pressable>
              </View>
              {loadingHistory ? (
                <ActivityIndicator />
              ) : conversations.length === 0 ? (
                <Text style={styles.emptyText}>No saved conversations yet.</Text>
              ) : (
                <FlatList
                  data={conversations}
                  keyExtractor={(item) => item.id}
                  renderItem={({ item }) => (
                    <Pressable style={styles.historyItem} onPress={() => selectConversation(item.id)}>
                      <Text style={styles.historyItemTitle} numberOfLines={2}>{item.title}</Text>
                      <Text style={styles.historyItemDate}>
                        {new Date(item.updated_at).toLocaleString()}
                      </Text>
                    </Pressable>
                  )}
                />
              )}
            </View>
          </View>
        </Modal>
      </RNKCKeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  conversationActions: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderColor: '#eee',
  },
  conversationActionText: { color: '#4A90E2', fontWeight: '600' },
  modalBackdrop: {
    flex: 1,
    justifyContent: 'flex-end',
    backgroundColor: 'rgba(0,0,0,0.35)',
  },
  historyPanel: {
    height: '70%',
    backgroundColor: '#fff',
    borderTopLeftRadius: 18,
    borderTopRightRadius: 18,
    padding: 18,
  },
  historyHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  historyTitle: { fontSize: 18, fontWeight: '700', color: '#222' },
  historyItem: { paddingVertical: 14, borderBottomWidth: 1, borderColor: '#eee' },
  historyItemTitle: { color: '#222', fontWeight: '600' },
  historyItemDate: { color: '#888', fontSize: 12, marginTop: 5 },
  pendingActionBox: { marginTop: 8, paddingTop: 8, borderTopWidth: 1, borderColor: '#ccc' },
  pendingActionSummary: { color: '#222', fontWeight: '600' },
  pendingActionButtons: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 10 },
  confirmActionText: { color: '#14804a', fontWeight: '700' },
  rejectActionText: { color: '#b42318', fontWeight: '700' },
  pendingActionStatus: { color: '#666', fontSize: 12, marginTop: 8, textTransform: 'capitalize' },
  list: { padding: 16, flexGrow: 1 },
  empty: { color: '#aaa', textAlign: 'center', marginTop: 40, fontSize: 14 },
  emptyContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 16 },
  emptyText: { color: '#aaa', textAlign: 'center', fontSize: 14 },
  bubbleContainer: { borderRadius: 12, padding: 10, marginBottom: 8, maxWidth: '80%' },
  userAlign: { backgroundColor: '#333', alignSelf: 'flex-end' },
  aiAlign: { backgroundColor: '#eee', alignSelf: 'flex-start' },
  userText: { color: '#fff' },
  aiText: { color: '#222' },
  userTimestamp: { color: '#ccc' },
  aiTimestamp: { color: '#888' },
  summaryButton: { padding: 10, alignItems: 'center', borderTopWidth: 1, borderColor: '#eee' },
  disabledSummaryButton: { backgroundColor: '#ccc' },
  summaryButtonText: { color: '#555', fontSize: 13 },
  inputRow: {
    flexDirection: 'row',
    padding: 12,
    borderTopWidth: 1,
    borderColor: '#eee',
    backgroundColor: '#fff',
  },
  input: {
    flex: 1,
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 20,
    paddingHorizontal: 14,
    paddingVertical: 8,
    marginRight: 8,
  },
  sendButton: { justifyContent: 'center' },
  disabledSendButton: { backgroundColor: '#ccc' },
  loadingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 8,
    backgroundColor: '#f0f0f0',
    borderRadius: 8,
    marginBottom: 8,
  },
  loadingText: { color: '#333', marginLeft: 8 },
  container: { flex: 1, backgroundColor: '#fff' },
  bubble: { borderRadius: 12, padding: 10, maxWidth: '80%' },
  sendText: { color: '#333', fontWeight: '600' },
  userBubble: { backgroundColor: '#333' },
  aiBubble: { backgroundColor: '#eee' },
  timestamp: { fontSize: 12, color: '#888', marginTop: 4 },
});
