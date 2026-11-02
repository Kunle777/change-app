import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, FlatList, Platform, Text, TextInput, TouchableOpacity, View } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { KeyboardAvoidingView } from 'react-native-keyboard-controller';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import * as Crypto from 'expo-crypto';
import ChatBubble from '../components/ai/ChatBubble';
import ChatEmptyState from '../components/ai/ChatEmptyState';
import HistorySheet from '../components/ai/HistorySheet';
import TypingIndicator from '../components/ai/TypingIndicator';
import type { ChatMessage } from '../components/ai/chatTypes';
import ElvynMascot from '../components/ElvynMascot';
import {
  confirmChatAction,
  getChatConversation,
  getChatConversations,
  getEveningSummary,
  getPendingChatActions,
  rejectChatAction,
  sendChatMessage,
  AIClientError,
} from '../services/ai';
import type { ChatConversation, PendingChatAction } from '../services/ai';
import { supabase } from '../services/supabase';
import { getMyProfile } from '../services/users';
import { formatClock } from '../utils/chatFormat';
import { useColors } from '../theme/colors';

const NEW_CONVERSATION = 'new';
const FRIENDLY_ERROR = "Elvyn couldn't complete that request. Please try again.";
const HISTORY_ERROR = "We couldn't load your conversations. Please try again.";

const activeKey = (userId: string) => `elvyn_ai_active_conversation:${userId}`;

function mapConversationMessages(
  detail: Awaited<ReturnType<typeof getChatConversation>>,
  pendingActions: PendingChatAction[],
): ChatMessage[] {
  const pendingById = new Map(pendingActions.map((action) => [action.id, action]));
  const mapped = detail.messages.flatMap((turn) => {
    const time = formatClock(turn.created_at);
    const pending = turn.pending_action_id
      ? pendingById.get(turn.pending_action_id)
      : undefined;
    return [
      { id: `${turn.id}-user`, role: 'user' as const, text: turn.question, timestamp: time },
      {
        id: `${turn.id}-ai`,
        role: 'ai' as const,
        text: turn.response,
        timestamp: time,
        pendingActionId: turn.pending_action_id ?? undefined,
        pendingActionSummary: pending?.summary,
        pendingActionStatus: pending?.status ?? (turn.pending_action_id ? 'invalid' : undefined),
      },
    ];
  });
  for (const turn of detail.messages) {
    if (!turn.resolved_action_id || !turn.resolved_action_status) continue;
    const proposedMessage = mapped.find(
      (message) => message.role === 'ai' && message.pendingActionId === turn.resolved_action_id,
    );
    if (proposedMessage) proposedMessage.pendingActionStatus = turn.resolved_action_status;
  }
  return mapped;
}

export default function AIScreen() {
  const colors = useColors();
  const insets = useSafeAreaInsets();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<ChatConversation[]>([]);
  const [historyVisible, setHistoryVisible] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [restoring, setRestoring] = useState(true);
  const [firstName, setFirstName] = useState('');
  const listRef = useRef<FlatList<ChatMessage>>(null);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const profile = await getMyProfile();
        if (active) setFirstName(profile.first_name ?? '');
      } catch {
        /* greeting works without a name */
      }
      try {
        const { data, error } = await supabase.auth.getUser();
        if (error || !data.user) return;
        const stored = await AsyncStorage.getItem(activeKey(data.user.id));
        if (stored === NEW_CONVERSATION) return;
        const available = await getChatConversations();
        if (!active) return;
        setConversations(available);
        const targetId = stored ?? available[0]?.id;
        if (!targetId) return;
        const [detail, pending] = await Promise.all([getChatConversation(targetId), getPendingChatActions(targetId)]);
        if (!active) return;
        setConversationId(detail.id);
        setMessages(mapConversationMessages(detail, pending));
        if (stored === null) await AsyncStorage.setItem(activeKey(data.user.id), detail.id);
      } catch (error) {
        console.log('Restore conversation failed:', error);
      } finally {
        if (active) setRestoring(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (messages.length > 0) requestAnimationFrame(() => listRef.current?.scrollToEnd({ animated: true }));
  }, [messages, sending]);

  const push = useCallback((message: Omit<ChatMessage, 'id' | 'timestamp'>) => {
    setMessages((prev) => [
      ...prev,
      { ...message, id: `${Date.now()}-${prev.length}-${message.role}`, timestamp: formatClock(new Date()) },
    ]);
  }, []);

  const rememberConversation = useCallback(async (id: string) => {
    try {
      const { data } = await supabase.auth.getUser();
      if (data.user) await AsyncStorage.setItem(activeKey(data.user.id), id);
    } catch (error) {
      console.log('Could not remember active conversation:', error);
    }
  }, []);

  const send = useCallback(
    async (text: string, opts?: { alreadyShown?: boolean; requestId?: string }) => {
      const message = text.trim();
      if (!message || sending) return;
      const requestId = opts?.requestId ?? Crypto.randomUUID();
      if (!opts?.alreadyShown) push({ role: 'user', text: message });
      setInput('');
      setSending(true);
      try {
        const result = await sendChatMessage(message, conversationId, requestId);
        if (result.conversation_id) {
          setConversationId(result.conversation_id);
          void rememberConversation(result.conversation_id);
        }
        push({
          role: 'ai',
          text: result.message,
          sources: result.memory_sources ?? [],
          pendingActionId: result.pending_action_id ?? undefined,
          pendingActionSummary: result.pending_action_summary ?? undefined,
          pendingActionStatus: result.pending_action_id ? 'pending' : undefined,
        });
        if (result.resolved_action_id && result.resolved_action_status) {
          setMessages((prev) => prev.map((item) => (
            item.role === 'ai' && item.pendingActionId === result.resolved_action_id
              ? { ...item, pendingActionStatus: result.resolved_action_status }
              : item
          )));
        }
      } catch (error) {
        const friendlyError = error instanceof AIClientError ? error.message : FRIENDLY_ERROR;
        push({
          role: 'ai',
          text: friendlyError,
          failed: true,
          retryText: message,
          retryRequestId: requestId,
        });
      } finally {
        setSending(false);
      }
    },
    [conversationId, push, rememberConversation, sending],
  );

  const retry = (failed: ChatMessage) => {
    if (!failed.retryText) return;
    setMessages((prev) => prev.filter((m) => m.id !== failed.id));
    void send(failed.retryText, { alreadyShown: true, requestId: failed.retryRequestId });
  };

  const decide = async (message: ChatMessage, confirm: boolean) => {
    if (sending || !message.pendingActionId) return;
    setSending(true);
    try {
      const result = confirm ? await confirmChatAction(message.pendingActionId) : await rejectChatAction(message.pendingActionId);
      const displayedStatus = result.status === 'error' && result.retryable
        ? 'pending'
        : result.status;
      setMessages((prev) => prev.map((m) => (m.id === message.id ? { ...m, pendingActionStatus: displayedStatus } : m)));
      const followUp: Record<string, string> = {
        created: `Done. I added${result.title ? ` "${result.title}"` : ' the task'}.`,
        updated: `Done. I updated${result.title ? ` "${result.title}"` : ' the task'}.`,
        cancelled: `Done. I cancelled${result.title ? ` "${result.title}"` : ' the task'}.`,
        rejected: 'No problem. Nothing was changed.',
        expired: 'That one expired. Ask me again and I will set it up fresh.',
        stale: 'That task changed in the meantime. Ask me again and I will use the latest version.',
        error: result.retryable
          ? "I couldn't complete that yet. Please check the details and try confirming again."
          : "That action is no longer available. Ask me to prepare it again if you still want it.",
      };
      push({ role: 'ai', text: followUp[result.status] ?? "That couldn't be completed. Please try again." });
    } catch (error) {
      console.log('Pending action failed:', error);
      push({ role: 'ai', text: "That didn't go through. Please try again in a moment." });
    } finally {
      setSending(false);
    }
  };

  const eveningSummary = async () => {
    if (sending) return;
    push({ role: 'user', text: 'Evening summary' });
    setSending(true);
    try {
      const result = await getEveningSummary();
      push({ role: 'ai', text: result.message });
    } catch (error) {
      console.log('Evening summary failed:', error);
      push({ role: 'ai', text: "I couldn't put your summary together just now. Please try again in a bit." });
    } finally {
      setSending(false);
    }
  };

  const loadHistory = async () => {
    setLoadingHistory(true);
    setHistoryError(null);
    try {
      setConversations(await getChatConversations());
    } catch (error) {
      console.log('History failed:', error);
      setHistoryError(HISTORY_ERROR);
    } finally {
      setLoadingHistory(false);
    }
  };

  const openHistory = () => {
    setHistoryVisible(true);
    void loadHistory();
  };

  const selectConversation = async (id: string) => {
    setLoadingHistory(true);
    setHistoryError(null);
    try {
      const [detail, pending] = await Promise.all([getChatConversation(id), getPendingChatActions(id)]);
      await rememberConversation(detail.id);
      setConversationId(detail.id);
      setMessages(mapConversationMessages(detail, pending));
      setHistoryVisible(false);
    } catch (error) {
      console.log('Open conversation failed:', error);
      setHistoryError("We couldn't open that conversation. Please try again.");
    } finally {
      setLoadingHistory(false);
    }
  };

  const newChat = async () => {
    try {
      const { data } = await supabase.auth.getUser();
      if (data.user) await AsyncStorage.setItem(activeKey(data.user.id), NEW_CONVERSATION);
    } catch (error) {
      console.log('Could not flag new conversation:', error);
    }
    setConversationId(null);
    setMessages([]);
    setInput('');
    setHistoryVisible(false);
    setHistoryError(null);
  };

  const lastAiIndex = (index: number) => messages[index + 1]?.role !== 'ai';
  const canSend = input.trim().length > 0 && !sending && !restoring;

  return (
    <View style={{ flex: 1, backgroundColor: colors.background }}>
      <View
        style={{
          backgroundColor: colors.heroBg,
          paddingTop: insets.top + 10,
          paddingBottom: 14,
          paddingHorizontal: 16,
          flexDirection: 'row',
          alignItems: 'center',
        }}
      >
        <ElvynMascot variant="supportive" size={34} />
        <View style={{ flex: 1, marginLeft: 10 }}>
          <Text style={{ color: '#fff', fontSize: 18, fontWeight: '800' }}>Ask Elvyn</Text>
          <Text style={{ color: '#C4C0F5', fontSize: 12 }}>Your personal coach</Text>
        </View>
        <TouchableOpacity
          onPress={openHistory}
          disabled={sending || restoring}
          accessibilityLabel="Conversation history"
          style={{ padding: 8, marginRight: 4 }}
        >
          <Ionicons name="time-outline" size={22} color="#fff" />
        </TouchableOpacity>
        <TouchableOpacity
          onPress={() => void newChat()}
          disabled={sending}
          accessibilityLabel="New chat"
          style={{ padding: 8 }}
        >
          <Ionicons name="create-outline" size={22} color="#fff" />
        </TouchableOpacity>
      </View>

      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
        {restoring ? (
          <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
            <ActivityIndicator color={colors.primary} />
            <Text style={{ color: colors.textMuted, marginTop: 10 }}>Opening your conversation…</Text>
          </View>
        ) : messages.length === 0 ? (
          <ChatEmptyState
            firstName={firstName}
            disabled={sending}
            onPrompt={(text) => void send(text)}
            onEveningSummary={() => void eveningSummary()}
          />
        ) : (
          <FlatList
            ref={listRef}
            data={messages}
            keyExtractor={(item) => item.id}
            contentContainerStyle={{ padding: 16, flexGrow: 1 }}
            keyboardShouldPersistTaps="handled"
            keyboardDismissMode={Platform.OS === 'ios' ? 'interactive' : 'on-drag'}
            renderItem={({ item, index }) => (
              <ChatBubble
                message={item}
                showAvatar={lastAiIndex(index)}
                busy={sending}
                onConfirm={(m) => void decide(m, true)}
                onReject={(m) => void decide(m, false)}
                onRetry={retry}
              />
            )}
            ListFooterComponent={sending ? <TypingIndicator /> : null}
          />
        )}

        {messages.length > 0 && !sending && (
          <View style={{ flexDirection: 'row', paddingHorizontal: 16, paddingBottom: 6 }}>
            <TouchableOpacity
              onPress={() => void eveningSummary()}
              style={{
                flexDirection: 'row',
                alignItems: 'center',
                backgroundColor: colors.primarySoft,
                borderRadius: 14,
                paddingHorizontal: 12,
                paddingVertical: 6,
              }}
            >
              <Ionicons name="moon-outline" size={14} color={colors.primary} />
              <Text style={{ color: colors.primary, fontWeight: '600', fontSize: 12, marginLeft: 6 }}>Evening summary</Text>
            </TouchableOpacity>
          </View>
        )}

        <View
          style={{
            flexDirection: 'row',
            alignItems: 'flex-end',
            paddingHorizontal: 12,
            paddingTop: 8,
            paddingBottom: Math.max(insets.bottom, 10),
            backgroundColor: colors.surface,
            borderTopWidth: 1,
            borderTopColor: colors.border,
          }}
        >
          <TextInput
            value={input}
            onChangeText={setInput}
            placeholder="Ask Elvyn anything…"
            placeholderTextColor={colors.textMuted}
            multiline
            maxLength={1000}
            editable={!restoring}
            style={{
              flex: 1,
              minHeight: 44,
              maxHeight: 120,
              color: colors.text,
              backgroundColor: colors.background,
              borderWidth: 1,
              borderColor: colors.border,
              borderRadius: 22,
              paddingHorizontal: 16,
              paddingTop: 12,
              paddingBottom: 12,
              marginRight: 8,
              fontSize: 15,
            }}
          />
          <TouchableOpacity
            onPress={() => void send(input)}
            disabled={!canSend}
            accessibilityRole="button"
            accessibilityLabel="Send message"
            style={{
              width: 44,
              height: 44,
              borderRadius: 22,
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: canSend ? colors.primary : colors.border,
            }}
          >
            <Ionicons name="arrow-up" size={22} color="#fff" />
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>

      <HistorySheet
        visible={historyVisible}
        conversations={conversations}
        activeId={conversationId}
        loading={loadingHistory}
        error={historyError}
        onClose={() => setHistoryVisible(false)}
        onSelect={(id) => void selectConversation(id)}
        onNewChat={() => void newChat()}
        onRetry={() => void loadHistory()}
      />
    </View>
  );
}
