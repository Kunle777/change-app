export type ChatMessage = {
  id: string;
  role: 'user' | 'ai';
  text: string;
  timestamp: string;
  pendingActionId?: string;
  pendingActionSummary?: string;
  pendingActionStatus?: string;
  sources?: import('./MemorySources').MemorySource[];
  /** A calm error bubble; `retryText` is what to resend. */
  failed?: boolean;
  retryText?: string;
};
