import { API_BASE_URL } from './api';
import { getAuthHeader } from './supabase';

type ClientTaskEvent = 'reminder_scheduled' | 'reminder_opened';

/** Best-effort event recording: event telemetry never delays or breaks app behavior. */
export async function recordTaskEvent(
  taskId: string,
  eventType: ClientTaskEvent,
  reminderTime?: string,
  notificationId?: string,
): Promise<void> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}/events`, {
      method: 'POST',
      headers: await getAuthHeader(),
      body: JSON.stringify({
        event_type: eventType,
        ...(reminderTime ? { reminder_time: reminderTime } : {}),
        ...(notificationId ? { notification_id: notificationId } : {}),
      }),
    });
    if (!response.ok) {
      console.warn(`Task event ${eventType} was not recorded (${response.status})`);
    }
  } catch (error) {
    console.warn(`Task event ${eventType} could not be sent`, error);
  }
}
