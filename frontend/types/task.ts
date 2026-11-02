export type TaskPriority = 'low' | 'medium' | 'high';
export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'cancelled';

export interface Task {
  id: string;
  title: string;
  description?: string | null;
  priority: TaskPriority;
  status: TaskStatus;
  category?: string | null;
  due_date?: string | null;
  due_date_is_all_day?: boolean | null;
  reminder_time?: string | null;
  snoozed_until?: string | null;
  recurrence?: string | null;
  has_series?: boolean;
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
