export interface BrainDump {
  id: string;
  content: string;
  source: 'text' | 'voice';
  is_converted: boolean;
  created_task_id: string | null;
  created_at: string;
  possible_task: boolean;
}

export interface ParsedTaskSuggestion {
  title: string;
  due_date?: string | null;
  time?: string | null;
  priority: string;
  recurrence_rule?: {
    frequency: 'daily' | 'weekly' | 'monthly';
    interval: number;
    days_of_week?: number[];
    timezone?: string;
    start_date?: string | null;
    end_date?: string | null;
    occurrence_limit?: number | null;
  } | null;
}
