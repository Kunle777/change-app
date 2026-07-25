import { api } from './api';
import { supabase } from './supabase';

async function getAuthHeader() {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  return { Authorization: `Bearer ${token}` };
}
export async function getTasks() {
  const headers = await getAuthHeader();
  const response = await api.get('/api/tasks', { headers });
  return response.data;
}

export async function createTask(taskData: {
  title: string;
  priority?: string;
  status?: string;
  description?: string;
  due_date?: string;
  reminder_time?: string;
  recurrence?: string;
}) {
  const headers = await getAuthHeader();
  const response = await api.post('/api/tasks', taskData, { headers });
  return response.data;
}

export async function updateTask(
  taskId: string,
  taskData: {
    title?: string;
    priority?: string;
    status?: string;
    description?: string;
    due_date?: string;
    reminder_time?: string;
    recurrence?: string;
  },
) {
  const headers = await getAuthHeader();
  const response = await api.patch(`/api/tasks/${taskId}`, taskData, { headers });
  return response.data;
}

export async function deleteTask(taskId: string) {
  const headers = await getAuthHeader();
  const response = await api.delete(`/api/tasks/${taskId}`, { headers });
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
