export type TaskPriority = 'low' | 'medium' | 'high';
export type TaskStatus = 'pending' | 'completed' | 'cancelled';

export interface Task {
  id: string;
  title: string;
  description?: string | null;
  priority: TaskPriority;
  status: TaskStatus;
  category?: string | null;
  due_date?: string | null;
  reminder_time?: string | null;
  snoozed_until?: string | null;
  recurrence?: string | null;
  series_id?: string | null;
  occurrence_date?: string | null;
  created_at: string;
  updated_at: string;
  priority_reminder: boolean;
}

export type TaskRecurrence = 'none' | 'daily' | 'weekly' | 'monthly';

export interface SuggestedAction {
  type: string;
  label: string;
  task_id?: string;
  screen?: string;
}

export interface AIMessage {
  role: 'user' | 'assistant';
  content: string;
  suggested_actions?: SuggestedAction[];
}
