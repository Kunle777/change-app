import { api } from './api';
import { API_BASE_URL } from './api';
import { getAuthHeader } from './supabase';
import { cancelTaskReminder, scheduleTaskReminder } from './notifications';
import { removeTaskFromCalendar } from './calendarSync';
import type { Task } from '../types/task';

export async function getTasks() {
  const headers = await getAuthHeader();
  const response = await api.get('/api/tasks', { headers });
  return response.data;
}

interface TaskInput {
  title: string;
  description?: string;
  priority: string;
  priority_reminder?: boolean;
  due_date?: string;
  reminder_time?: string;
  recurrence?: string;
  recurrence_rule?: {
    frequency: 'daily' | 'weekly' | 'monthly';
    interval?: number;
    days_of_week?: number[];
    start_date: string;
    local_time?: string;
    timezone?: string;
    end_date?: string;
    occurrence_limit?: number;
  };
}

export async function createTask(input: TaskInput): Promise<Task> {
  const res = await fetch(`${API_BASE_URL}/api/tasks`, {
    method: 'POST',
    headers: await getAuthHeader(),
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Couldn't create task (${res.status}): ${detail}`);
  }
  const task: Task = await res.json();
  if (task.reminder_time)
    await scheduleTaskReminder(task.id, task.title, new Date(task.reminder_time), task.priority_reminder);
  return task;
}

export async function updateTask(taskId: string, input: Partial<TaskInput>): Promise<Task> {
  const res = await fetch(`${API_BASE_URL}/api/tasks/${taskId}`, {
    method: 'PATCH',
    headers: await getAuthHeader(),
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Couldn't update task (${res.status}): ${detail}`);
  }
  const task: Task = await res.json();
  await cancelTaskReminder(taskId);
  if (task.reminder_time)
    await scheduleTaskReminder(task.id, task.title, new Date(task.reminder_time), task.priority_reminder);
  return task;
}

export async function deleteTask(taskId: string) {
  const headers = await getAuthHeader();
  const response = await api.delete(`/api/tasks/${taskId}`, { headers });
  await removeTaskFromCalendar(taskId);
  return response.data;
}

export async function markTaskDone(taskId: string) {
  const headers = await getAuthHeader();
  const response = await api.post(`/api/tasks/${taskId}/done`, null, { headers });
  return response.data;
}

export async function snoozeTask(taskId: string) {
  const headers = await getAuthHeader();
  const response = await api.post(`/api/tasks/${taskId}/snooze`, null, { headers });
  return response.data;
}

export async function getTaskById(taskId: string) {
  const headers = await getAuthHeader(); // however your existing functions get this
  const response = await api.get(`/api/tasks/${taskId}`, { headers });
  return response.data;
}

export async function breakdownTask(taskId: string) {
  const headers = await getAuthHeader();
  const response = await api.post(`/api/tasks/${taskId}/breakdown`, {}, { headers });
  return response.data;
}

// "Not now" — friendlier wrapper over the existing snooze mechanism.
// Options map to a concrete new reminder_time.
export async function notNowTask(
  taskId: string,
  option: 'later_today' | 'tomorrow' | 'custom',
  customTime?: Date,
): Promise<Task> {
  let snoozedUntil: Date;
  const now = new Date();

  if (option === 'later_today') {
    snoozedUntil = new Date(now.getTime() + 3 * 60 * 60 * 1000); // +3h
  } else if (option === 'tomorrow') {
    snoozedUntil = new Date(now);
    snoozedUntil.setDate(snoozedUntil.getDate() + 1);
    snoozedUntil.setHours(9, 0, 0, 0);
  } else {
    if (!customTime) throw new Error('customTime required for custom option');
    snoozedUntil = customTime;
  }

  const res = await fetch(`${API_BASE_URL}/api/tasks/${taskId}/snooze`, {
    method: 'POST',
    headers: await getAuthHeader(),
    body: JSON.stringify({ snoozed_until: snoozedUntil.toISOString() }),
  });
  if (!res.ok) throw new Error("Couldn't postpone this task.");
  const task: Task = await res.json();

  await cancelTaskReminder(taskId);
  await scheduleTaskReminder(task.id, task.title, snoozedUntil, task.priority_reminder);

  return task;
}

// "Reschedule" — genuinely changes the planned due date/time, not a snooze.
export async function rescheduleTask(
  taskId: string,
  dueDate?: Date,
  reminderTime?: Date,
): Promise<Task> {
  const res = await fetch(`${API_BASE_URL}/api/tasks/${taskId}/reschedule`, {
    method: 'PATCH',
    headers: await getAuthHeader(),
    body: JSON.stringify({
      due_date: dueDate?.toISOString(),
      reminder_time: reminderTime?.toISOString(),
    }),
  });
  if (!res.ok) throw new Error("Couldn't reschedule this task.");
  const task: Task = await res.json();

  await cancelTaskReminder(taskId);
  if (reminderTime) await scheduleTaskReminder(task.id, task.title, reminderTime, task.priority_reminder);

  return task;
}

// Completion now owns its own side effects — the screen no longer
// needs to remember to cancel the notification separately.
export async function completeTask(taskId: string): Promise<Task> {
  const res = await fetch(`${API_BASE_URL}/api/tasks/${taskId}/done`, {
    method: 'POST',
    headers: await getAuthHeader(),
  });
  if (!res.ok) throw new Error("Couldn't mark this task as done.");
  const task: Task = await res.json();

  await cancelTaskReminder(taskId);

  return task;
}

export async function cancelTask(taskId: string): Promise<Task> {
  const res = await fetch(`${API_BASE_URL}/api/tasks/${taskId}/cancel`, {
    method: 'POST',
    headers: await getAuthHeader(),
  });
  if (!res.ok) throw new Error("Couldn't cancel this task.");
  const task: Task = await res.json();
  await cancelTaskReminder(taskId);
  return task;
}

export type VoiceTaskParse = {
  title: string;
  due_date: string | null;
  time: string | null;
  priority: 'low' | 'medium' | 'high';
};

export async function parseVoiceTask(transcript: string): Promise<VoiceTaskParse> {
  const now = new Date();
  const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
  const response = await fetch(`${API_BASE_URL}/api/tasks/parse-voice`, {
    method: 'POST',
    headers: await getAuthHeader(),
    body: JSON.stringify({ transcript, today }),
  });
  if (!response.ok) throw new Error("Couldn't understand that. Please try again.");
  return response.json();
}

export type UpcomingReminderTask = Pick<Task, 'id' | 'title' | 'reminder_time' | 'priority_reminder'>;

export async function getUpcomingTasks(days = 14): Promise<UpcomingReminderTask[]> {
  const response = await fetch(`${API_BASE_URL}/api/tasks/upcoming?days=${days}`, {
    headers: await getAuthHeader(),
  });
  if (!response.ok) throw new Error("Couldn't sync upcoming reminders.");
  return response.json();
}

export async function getCalendarDates(year: number, month: number): Promise<string[]> {
  const res = await fetch(`${API_BASE_URL}/api/tasks/calendar-dates?year=${year}&month=${month}`, {
    headers: await getAuthHeader(),
  });
  if (!res.ok) throw new Error("Couldn't load calendar.");
  const data = await res.json();
  return data.dates;
}

export async function getTasksByDate(dateStr: string, filter: string = 'all'): Promise<Task[]> {
  const res = await fetch(`${API_BASE_URL}/api/tasks/by-date?date=${dateStr}&status=${filter}`, {
    headers: await getAuthHeader(),
  });
  if (!res.ok) throw new Error("Couldn't load tasks.");
  return res.json();
}

export async function stopTaskSeries(taskId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}/stop-series`, {
    method: 'POST',
    headers: await getAuthHeader(),
  });
  if (!response.ok) throw new Error("Couldn't stop this recurring series.");
}

export type SeriesEditScope = 'occurrence' | 'this_and_future' | 'entire_series';

export async function editTaskSeries(
  taskId: string,
  scope: SeriesEditScope,
  changes: { title: string; description?: string | null; priority: 'low' | 'medium' | 'high' },
): Promise<Task> {
  const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}/series-edit`, {
    method: 'PATCH',
    headers: { ...(await getAuthHeader()), 'Content-Type': 'application/json' },
    body: JSON.stringify({ scope, ...changes }),
  });
  if (!response.ok) throw new Error("Couldn't update this recurring task.");
  return response.json();
}
