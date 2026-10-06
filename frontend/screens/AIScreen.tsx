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
} from 'react-native';
import { KeyboardAvoidingView as RNKCKeyboardAvoidingView } from 'react-native-keyboard-controller';
import { SafeAreaView } from 'react-native-safe-area-context';
import { sendChatMessage, getEveningSummary } from '../services/ai';

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
      timestamp: new Date().toLocaleTimeString(),
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
      const result = await sendChatMessage(userText);
      addMessage('ai', result.response);
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
      addMessage('ai', result.response);
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
      </RNKCKeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
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
