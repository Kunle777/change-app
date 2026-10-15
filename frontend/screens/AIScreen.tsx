import React, { useState, useRef, useEffect, useMemo } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  StyleSheet,
  Platform,
  ActivityIndicator,
  Modal,
  Pressable,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { KeyboardAvoidingView } from 'react-native-keyboard-controller';
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
import { supabase } from '../services/supabase';
import { useColors, type ThemeColors } from '../theme/colors';

type Message = {
  id: string;
  role: 'user' | 'ai';
  text: string;
  timestamp: string;
  pendingActionId?: string;
  pendingActionSummary?: string;
  pendingActionStatus?: string;
};

const NEW_CONVERSATION = 'new';

function getActiveConversationKey(userId: string) {
  return `elvyn_ai_active_conversation:${userId}`;
}

function mapConversationMessages(
  detail: Awaited<ReturnType<typeof getChatConversation>>,
  pendingActions: PendingChatAction[],
): Message[] {
  const pendingById = new Map<string, PendingChatAction>(
    pendingActions.map((action) => [action.id, action]),
  );
  return detail.messages.flatMap((turn) => [
    {
      id: `${turn.id}-user`,
      role: 'user' as const,
      text: turn.question,
      timestamp: turn.created_at ? new Date(turn.created_at).toLocaleTimeString() : '',
    },
    {
      id: `${turn.id}-ai`,
      role: 'ai' as const,
      text: turn.response,
      timestamp: turn.created_at ? new Date(turn.created_at).toLocaleTimeString() : '',
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
  ]);
}

export default function AIScreen() {
  const colors = useColors();
  const styles = useMemo(() => makeStyles(colors), [colors]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<ChatConversation[]>([]);
  const [historyVisible, setHistoryVisible] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [restoringConversation, setRestoringConversation] = useState(true);
  const flatListRef = useRef<FlatList>(null);

  useEffect(() => {
    let active = true;

    const restoreConversation = async () => {
      try {
        const { data, error } = await supabase.auth.getUser();
        if (error) throw error;
        if (!data.user) return;

        const storageKey = getActiveConversationKey(data.user.id);
        const storedId = await AsyncStorage.getItem(storageKey);
        if (storedId === NEW_CONVERSATION) return;

        const availableConversations = await getChatConversations();
        if (!active) return;
        setConversations(availableConversations);

        const targetId = storedId ?? availableConversations[0]?.id;
        if (!targetId) return;

        const detail = await getChatConversation(targetId);
        const pendingActions = await getPendingChatActions(targetId);
        if (!active) return;

        setConversationId(detail.id);
        setMessages(mapConversationMessages(detail, pendingActions));
        if (storedId === null) {
          await AsyncStorage.setItem(storageKey, detail.id);
        }
      } catch (error) {
        if (active) {
          setHistoryError(
            error instanceof Error ? error.message : 'Could not restore your conversation.',
          );
        }
      } finally {
        if (active) setRestoringConversation(false);
      }
    };

    void restoreConversation();
    return () => {
      active = false;
    };
  }, []);

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
    setHistoryError(null);
    try {
      setConversations(await getChatConversations());
    } catch (error) {
      setHistoryError(
        error instanceof Error ? error.message : 'Could not load conversation history.',
      );
    } finally {
      setLoadingHistory(false);
    }
  };

  const selectConversation = async (id: string) => {
    setLoadingHistory(true);
    setHistoryError(null);
    try {
      const detail = await getChatConversation(id);
      const pendingActions = await getPendingChatActions(id);
      const { data, error } = await supabase.auth.getUser();
      if (error) throw error;
      if (!data.user) throw new Error('Please log in again to open this conversation.');
      await AsyncStorage.setItem(getActiveConversationKey(data.user.id), detail.id);
      setConversationId(detail.id);
      setMessages(mapConversationMessages(detail, pendingActions));
      setHistoryVisible(false);
    } catch (error) {
      setHistoryError(
        error instanceof Error ? error.message : 'Could not load this conversation.',
      );
    } finally {
      setLoadingHistory(false);
    }
  };

  const startNewConversation = async () => {
    try {
      const { data, error } = await supabase.auth.getUser();
      if (error) throw error;
      if (!data.user) throw new Error('Please log in again to start a conversation.');
      await AsyncStorage.setItem(
        getActiveConversationKey(data.user.id),
        NEW_CONVERSATION,
      );
      setConversationId(null);
      setMessages([]);
      setInput('');
      setHistoryVisible(false);
      setHistoryError(null);
    } catch (error) {
      setHistoryError(
        error instanceof Error ? error.message : 'Could not start a new conversation.',
      );
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
      if (result.conversation_id) {
        addMessage(
          'ai',
          result.message,
          result.pending_action_id
            ? { id: result.pending_action_id, summary: result.pending_action_summary }
            : undefined,
        );
        try {
          const { data, error } = await supabase.auth.getUser();
          if (error) throw error;
          if (data.user) {
            await AsyncStorage.setItem(
              getActiveConversationKey(data.user.id),
              result.conversation_id,
            );
          }
        } catch (storageError) {
          console.warn('Could not remember the active AI conversation', storageError);
        }
      } else {
        addMessage('ai', result.message);
      }
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
      <KeyboardAvoidingView
        style={styles.container}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={0}
      >
        <View style={styles.conversationActions}>
          <TouchableOpacity onPress={openHistory} disabled={sending || restoringConversation}>
            <Text style={styles.conversationActionText}>History</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={() => void startNewConversation()} disabled={sending}>
            <Text style={styles.conversationActionText}>New chat</Text>
          </TouchableOpacity>
        </View>
        {restoringConversation && (
          <View style={styles.emptyContainer}>
            <ActivityIndicator color={colors.primary} />
            <Text style={styles.emptyText}>Restoring your conversation...</Text>
          </View>
        )}
        {!restoringConversation && historyError && !historyVisible && (
          <Text style={styles.historyError}>{historyError}</Text>
        )}
        {!restoringConversation && messages.length === 0 && (
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
          keyboardShouldPersistTaps="handled"
          keyboardDismissMode={Platform.OS === 'ios' ? 'interactive' : 'on-drag'}
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
            <ActivityIndicator size="small" color={colors.primary} />
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
            placeholderTextColor={colors.textMuted}
            multiline
            maxLength={1000}
            editable={!sending && !restoringConversation}
          />
          <TouchableOpacity
            style={[
              styles.sendButton,
              (!input.trim() || sending || restoringConversation) && styles.disabledSendButton,
            ]}
            onPress={handleSend}
            disabled={!input.trim() || sending || restoringConversation}
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
                <ActivityIndicator color={colors.primary} />
              ) : historyError ? (
                <Text style={styles.historyError}>{historyError}</Text>
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
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function makeStyles(colors: ThemeColors) {
  return StyleSheet.create({
    conversationActions: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      paddingHorizontal: 16,
      paddingVertical: 12,
      borderBottomWidth: 1,
      borderColor: colors.border,
      backgroundColor: colors.surface,
    },
    conversationActionText: { color: colors.primary, fontWeight: '700' },
    modalBackdrop: {
      flex: 1,
      justifyContent: 'flex-end',
      backgroundColor: 'rgba(0,0,0,0.45)',
    },
    historyPanel: {
      height: '70%',
      backgroundColor: colors.surface,
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
    historyTitle: { fontSize: 18, fontWeight: '700', color: colors.text },
    historyItem: { paddingVertical: 14, borderBottomWidth: 1, borderColor: colors.border },
    historyItemTitle: { color: colors.text, fontWeight: '600' },
    historyItemDate: { color: colors.textMuted, fontSize: 12, marginTop: 5 },
    historyError: {
      color: colors.danger,
      backgroundColor: colors.surface,
      paddingHorizontal: 16,
      paddingVertical: 10,
    },
    pendingActionBox: { marginTop: 8, paddingTop: 8, borderTopWidth: 1, borderColor: colors.border },
    pendingActionSummary: { color: colors.text, fontWeight: '600' },
    pendingActionButtons: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 10 },
    confirmActionText: { color: colors.success, fontWeight: '700' },
    rejectActionText: { color: colors.danger, fontWeight: '700' },
    pendingActionStatus: {
      color: colors.textMuted,
      fontSize: 12,
      marginTop: 8,
      textTransform: 'capitalize',
    },
    list: { padding: 16, flexGrow: 1 },
    emptyContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 16 },
    emptyText: { color: colors.textMuted, textAlign: 'center', fontSize: 14, marginTop: 8 },
    bubbleContainer: { borderRadius: 16, padding: 12, marginBottom: 10, maxWidth: '88%' },
    userAlign: { backgroundColor: colors.primary, alignSelf: 'flex-end' },
    aiAlign: {
      backgroundColor: colors.surface,
      borderWidth: 1,
      borderColor: colors.border,
      alignSelf: 'flex-start',
    },
    userText: { color: '#FFFFFF', fontSize: 15, lineHeight: 21 },
    aiText: { color: colors.text, fontSize: 15, lineHeight: 21 },
    userTimestamp: { color: '#E0DEFF' },
    aiTimestamp: { color: colors.textMuted },
    summaryButton: {
      padding: 12,
      alignItems: 'center',
      borderTopWidth: 1,
      borderColor: colors.border,
      backgroundColor: colors.surface,
    },
    disabledSummaryButton: { opacity: 0.55 },
    summaryButtonText: { color: colors.primary, fontSize: 13, fontWeight: '600' },
    inputRow: {
      flexDirection: 'row',
      alignItems: 'flex-end',
      padding: 12,
      borderTopWidth: 1,
      borderColor: colors.border,
      backgroundColor: colors.surface,
    },
    input: {
      flex: 1,
      minHeight: 44,
      maxHeight: 120,
      color: colors.text,
      backgroundColor: colors.background,
      borderWidth: 1,
      borderColor: colors.border,
      borderRadius: 20,
      paddingHorizontal: 14,
      paddingVertical: 10,
      marginRight: 8,
      fontSize: 16,
      textAlignVertical: 'top',
    },
    sendButton: {
      minHeight: 44,
      justifyContent: 'center',
      alignItems: 'center',
      paddingHorizontal: 16,
      borderRadius: 22,
      backgroundColor: colors.primary,
    },
    disabledSendButton: { backgroundColor: colors.border },
    loadingContainer: {
      flexDirection: 'row',
      alignItems: 'center',
      padding: 10,
      backgroundColor: colors.surface,
      borderRadius: 8,
      marginHorizontal: 16,
      marginBottom: 8,
    },
    loadingText: { color: colors.text, marginLeft: 8 },
    container: { flex: 1, backgroundColor: colors.background },
    bubble: { borderRadius: 12, maxWidth: '100%' },
    sendText: { color: '#FFFFFF', fontWeight: '700' },
    userBubble: { backgroundColor: colors.primary },
    aiBubble: { backgroundColor: colors.surface },
    timestamp: { fontSize: 11, marginTop: 5 },
  });
}
