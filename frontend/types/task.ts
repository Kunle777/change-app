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
  created_at: string;
  updated_at: string;
}
