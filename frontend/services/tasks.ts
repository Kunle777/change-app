import { api } from "./api";

export async function getTasks(token: string) {
  const response = await api.get("/api/tasks", {
    headers: { Authorization: `Bearer ${token}` },
  });
  return response.data;
}

export async function createTask(
  token: string,
  taskData: {
    title: string;
    priority?: string;
    status?: string;
    description?: string;
    due_date?: string;
    reminder_time?: string;
    recurrence?: string;
  }
) {
  const response = await api.post("/api/tasks", taskData, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return response.data;
}

export async function updateTask(
  token: string,
  taskId: string,
  taskData: {
    title?: string;
    priority?: string;
    status?: string;
    description?: string;
    due_date?: string;
    reminder_time?: string;
    recurrence?: string;
  }
) {
  const response = await api.patch(`/api/tasks/${taskId}`, taskData, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return response.data;
}

export async function deleteTask(token: string, taskId: string) {
  const response = await api.delete(`/api/tasks/${taskId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return response.data;
}

export async function markTaskDone(token: string, taskId: string) {
  const response = await api.post(`/api/tasks/${taskId}done`, null, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return response.data;
}
