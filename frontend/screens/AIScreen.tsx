import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  StyleSheet,
  Platform,
  ActivityIndicator,
} from 'react-native';
import { KeyboardAvoidingView } from 'react-native-keyboard-controller';
import { SafeAreaView } from 'react-native-safe-area-context';
import { sendAIMessage, getEveningSummary } from '../services/ai';

type Message = { id: string; role: 'user' | 'ai'; text: string; timestamp: string };

export default function AIScreen() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const flatListRef = useRef<FlatList>(null);

  useEffect(() => {
    if (messages.length > 0) {
      flatListRef.current?.scrollToEnd({ animated: true });
    }
  }, [messages, sending]);

  const addMessage = (role: 'user' | 'ai', text: string) => {
    const newMessage: Message = {
      id: Date.now().toString() + role,
      role,
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, newMessage]);
  };

  const handleSend = async () => {
    if (!input.trim() || sending) return;
    const userText = input.trim();
    addMessage('user', userText);
    setInput('');
    setSending(true);
    try {
      const result = await sendAIMessage(userText);
      addMessage('ai', result.message || result.response);
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
      addMessage('ai', result.message || result.response);
    } catch (err: any) {
      addMessage('ai', `⚠️ ${err.message}`);
    } finally {
      setSending(false);
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={['top', 'left', 'right']}>
      <KeyboardAvoidingView
        style={styles.container}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
      >
        {messages.length === 0 ? (
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyText}>
              Ask anything — your tasks, goals, or just how you're doing.
            </Text>
          </View>
        ) : (
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
                  <Text style={isUser ? styles.userText : styles.aiText}>{item.text}</Text>
                  <Text
                    style={[styles.timestamp, isUser ? styles.userTimestamp : styles.aiTimestamp]}
                  >
                    {item.timestamp}
                  </Text>
                </View>
              );
            }}
          />
        )}

        {sending && (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="small" color="#4F46E5" />
            <Text style={styles.loadingText}>Elvyn is thinking...</Text>
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
            placeholder="Ask Elvyn..."
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
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  list: { padding: 16, flexGrow: 1 },
  emptyContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 16 },
  emptyText: { color: '#aaa', textAlign: 'center', fontSize: 14 },
  bubbleContainer: { borderRadius: 14, padding: 12, marginBottom: 10, maxWidth: '85%' },
  userAlign: { backgroundColor: '#4F46E5', alignSelf: 'flex-end' },
  aiAlign: { backgroundColor: '#EEF0FF', alignSelf: 'flex-start' },
  userText: { color: '#fff', fontSize: 14 },
  aiText: { color: '#111', fontSize: 14 },
  timestamp: { fontSize: 10, marginTop: 4, textAlign: 'right' },
  userTimestamp: { color: '#E0E7FF' },
  aiTimestamp: { color: '#6B7280' },
  summaryButton: { padding: 10, alignItems: 'center', borderTopWidth: 1, borderColor: '#eee' },
  disabledSummaryButton: { backgroundColor: '#f5f5f5' },
  summaryButtonText: { color: '#4F46E5', fontSize: 13, fontWeight: '500' },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    borderTopWidth: 1,
    borderColor: '#eee',
    backgroundColor: '#fff',
  },
  input: {
    flex: 1,
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 8,
    marginRight: 8,
    maxHeight: 100,
  },
  sendButton: {
    backgroundColor: '#4F46E5',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 20,
    justifyContent: 'center',
  },
  disabledSendButton: { backgroundColor: '#ccc' },
  sendText: { color: '#fff', fontWeight: '600' },
  loadingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  loadingText: { color: '#666', marginLeft: 8, fontSize: 12 },
});
