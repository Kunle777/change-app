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
  resolved_action_id: string | null;
  resolved_action_status: string | null;
};
export type ChatConversationDetail = ChatConversation & { messages: ChatConversationTurn[] };
export type PendingChatAction = { id: string; summary: string; expires_at: string; status: string };

export class AIClientError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly requestId?: string,
  ) {
    super(message);
    this.name = 'AIClientError';
  }
}

const AI_ERROR_MESSAGES: Record<string, string> = {
  provider_quota: "Elvyn's AI service is at its current usage limit. Please try again later.",
  provider_rate_limit: "Elvyn's AI service is handling too many requests. Please try again shortly.",
  provider_auth: "Elvyn's AI service is temporarily unavailable. Please contact support if this continues.",
  provider_outage: "Elvyn's AI service is temporarily unavailable. Please try again shortly.",
  request_timeout: 'Elvyn took too long to respond. Please try again.',
  network_error: "Elvyn couldn't connect to a required service. Please check your connection and try again.",
  database_error: "Elvyn couldn't access the information needed for this request. Please try again.",
  invalid_model_response: "Elvyn couldn't form a reliable response. Please try asking another way.",
  backend_error: "Elvyn couldn't complete that request. Please try again.",
  app_usage_limit: "You've reached today's Elvyn message limit. Please try again tomorrow.",
};

function friendlyAIError(code: string, requestId?: string) {
  const message = AI_ERROR_MESSAGES[code] ?? AI_ERROR_MESSAGES.backend_error;
  return requestId ? `${message} (Reference: ${requestId})` : message;
}

async function parseResponse(response: Response, fallback: string) {
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error((err as any).detail || fallback);
  }
  return response.json();
}

export async function sendChatMessage(
  message: string,
  conversationId: string | null | undefined,
  idempotencyKey: string,
) {
  const headers = await getAuthHeader();
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 45000);
  try {
    const response = await fetch(`${API_BASE_URL}/api/ai/chat`, {
      method: 'POST',
      headers,
      signal: controller.signal,
      body: JSON.stringify({
        message,
        conversation_id: conversationId ?? undefined,
        idempotency_key: idempotencyKey,
      }),
    });
    const requestId = response.headers.get('x-request-id') ?? undefined;
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      const code = typeof body.code === 'string'
        ? body.code
        : response.status === 429
          ? 'app_usage_limit'
          : 'backend_error';
      throw new AIClientError(
        code,
        friendlyAIError(code, body.request_id ?? requestId),
        body.request_id ?? requestId,
      );
    }
    return response.json();
  } catch (error) {
    if (error instanceof AIClientError) throw error;
    if (error instanceof Error && error.name === 'AbortError') {
      throw new AIClientError(
        'request_timeout',
        friendlyAIError('request_timeout'),
      );
    }
    if (error instanceof TypeError) {
      throw new AIClientError(
        'network_error',
        friendlyAIError('network_error'),
      );
    }
    throw new AIClientError(
      'backend_error',
      friendlyAIError('backend_error'),
    );
  } finally {
    clearTimeout(timeout);
  }
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
