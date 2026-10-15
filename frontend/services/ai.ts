import { getAuthHeader } from './supabase';
import { API_BASE_URL } from './api';

export type ChatConversation = { id: string; title: string; updated_at: string };
export type ChatConversationTurn = {
  id: string;
  question: string;
  response: string;
  intent: string | null;
  created_at: string | null;
  pending_action_id: string | null;
};
export type ChatConversationDetail = ChatConversation & { messages: ChatConversationTurn[] };
export type PendingChatAction = { id: string; summary: string; expires_at: string };

async function parseResponse(response: Response, fallback: string) {
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error((err as any).detail || fallback);
  }
  return response.json();
}

export async function sendChatMessage(message: string, conversationId?: string | null) {
  const headers = await getAuthHeader();
  const response = await fetch(`${API_BASE_URL}/api/ai/chat`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ message, conversation_id: conversationId ?? undefined }),
  });
  return parseResponse(response, 'AI request failed');
}

export async function getChatConversations(): Promise<ChatConversation[]> {
  const headers = await getAuthHeader();
  const response = await fetch(`${API_BASE_URL}/api/ai/conversations`, { headers });
  return parseResponse(response, 'Could not load conversation history');
}

export async function getChatConversation(id: string): Promise<ChatConversationDetail> {
  const headers = await getAuthHeader();
  const response = await fetch(
    `${API_BASE_URL}/api/ai/conversations/${encodeURIComponent(id)}`,
    { headers },
  );
  return parseResponse(response, 'Could not load this conversation');
}

export async function getPendingChatActions(conversationId: string): Promise<PendingChatAction[]> {
  const headers = await getAuthHeader();
  const response = await fetch(
    `${API_BASE_URL}/api/ai/actions/pending?conversation_id=${encodeURIComponent(conversationId)}`,
    { headers },
  );
  return parseResponse(response, 'Could not load pending actions');
}

export async function confirmChatAction(id: string) {
  const headers = await getAuthHeader();
  const response = await fetch(`${API_BASE_URL}/api/ai/actions/${encodeURIComponent(id)}/confirm`, {
    method: 'POST',
    headers,
  });
  return parseResponse(response, 'Could not confirm this action');
}

export async function rejectChatAction(id: string) {
  const headers = await getAuthHeader();
  const response = await fetch(`${API_BASE_URL}/api/ai/actions/${encodeURIComponent(id)}/reject`, {
    method: 'POST',
    headers,
  });
  return parseResponse(response, 'Could not reject this action');
}

export async function getEveningSummary() {
  const headers = await getAuthHeader();
  const response = await fetch(`${API_BASE_URL}/api/ai/evening-summary`, {
    method: 'POST',
    headers,
  });
  return parseResponse(response, 'Failed to get summary');
}
