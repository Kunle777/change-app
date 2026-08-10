import React, { useState, useRef } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, FlatList,
  StyleSheet, KeyboardAvoidingView, Platform, ActivityIndicator,
} from 'react-native';
import { sendChatMessage, getEveningSummary } from '../services/ai';

type Message = { id: string; role: 'user' | 'ai'; text: string };

export default function AIScreen() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const listRef = useRef<FlatList>(null);

  const addMessage = (role: 'user' | 'ai', text: string) => {
    setMessages((prev) => [...prev, { id: Date.now().toString() + role, role, text }]);
    setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 100);
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
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <FlatList
        ref={listRef}
        data={messages}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          <Text style={styles.empty}>Ask anything — your tasks, goals, or just how you're doing.</Text>
        }
        renderItem={({ item }) => (
          <View style={[styles.bubble, item.role === 'user' ? styles.userBubble : styles.aiBubble]}>
            <Text style={item.role === 'user' ? styles.userText : styles.aiText}>{item.text}</Text>
          </View>
        )}
      />

      {sending && <ActivityIndicator style={{ marginBottom: 8 }} />}

      <TouchableOpacity style={styles.summaryButton} onPress={handleEveningSummary} disabled={sending}>
        <Text style={styles.summaryButtonText}>Get evening summary</Text>
      </TouchableOpacity>

      <View style={styles.inputRow}>
        <TextInput
          style={styles.input}
          value={input}
          onChangeText={setInput}
          placeholder="Ask something..."
          onSubmitEditing={handleSend}
          returnKeyType="send"
        />
        <TouchableOpacity onPress={handleSend} disabled={sending} style={styles.sendButton}>
          <Text style={styles.sendText}>Send</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  list: { padding: 16, flexGrow: 1 },
  empty: { color: '#aaa', textAlign: 'center', marginTop: 40, fontSize: 14 },
  bubble: { borderRadius: 12, padding: 10, marginBottom: 8, maxWidth: '80%' },
  userBubble: { backgroundColor: '#333', alignSelf: 'flex-end' },
  aiBubble: { backgroundColor: '#eee', alignSelf: 'flex-start' },
  userText: { color: '#fff' },
  aiText: { color: '#222' },
  summaryButton: { padding: 10, alignItems: 'center', borderTopWidth: 1, borderColor: '#eee' },
  summaryButtonText: { color: '#555', fontSize: 13 },
  inputRow: { flexDirection: 'row', padding: 12, borderTopWidth: 1, borderColor: '#eee', backgroundColor: '#fff' },
  input: { flex: 1, borderWidth: 1, borderColor: '#ccc', borderRadius: 20, paddingHorizontal: 14, paddingVertical: 8, marginRight: 8 },
  sendButton: { justifyContent: 'center' },
  sendText: { color: '#333', fontWeight: '600' },
});
