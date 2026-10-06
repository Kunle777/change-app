import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';
import * as Calendar from 'expo-calendar';

const EVENT_KEY_PREFIX = 'calendar_event_';
const TARGET_CALENDAR_KEY = 'calendar_sync_target_id';

type WritableCalendar = {
  id: string;
  allowsModifications: boolean;
  isPrimary?: boolean;
};

export interface CalendarSyncTask {
  id: string;
  title: string;
  description?: string | null;
  due_date?: string | null;
  reminder_time?: string | null;
  calendar_sync?: boolean;
}

const eventKey = (taskId: string) => `${EVENT_KEY_PREFIX}${taskId}`;

function validDate(value?: string | null): Date | null {
  const date = value ? new Date(value) : null;
  return date && Number.isFinite(date.getTime()) ? date : null;
}

// Invoke only from an explicit calendar-sync action; never at app startup.
export async function requestCalendarPermission(): Promise<boolean> {
  if (Platform.OS === 'web') return false;
  const { status } = await Calendar.requestCalendarPermissionsAsync();
  return status === 'granted';
}

async function getWritableCalendarId(): Promise<string | null> {
  if (Platform.OS === 'web') return null;
  const calendars = await Calendar.getCalendarsAsync(Calendar.EntityTypes.EVENT);
  const storedId = await AsyncStorage.getItem(TARGET_CALENDAR_KEY);
  const stored = calendars.find((item) => item.id === storedId && item.allowsModifications);
  if (stored) return stored.id;

  let calendar: WritableCalendar | undefined;
  if (Platform.OS === 'ios') {
    const defaultCalendar = await Calendar.getDefaultCalendarAsync();
    if (defaultCalendar?.allowsModifications) calendar = defaultCalendar;
  } else {
    calendar = calendars.find((item) => item.allowsModifications && item.isPrimary)
      ?? calendars.find((item) => item.allowsModifications);
  }
  if (!calendar) return null;
  await AsyncStorage.setItem(TARGET_CALENDAR_KEY, calendar.id);
  return calendar.id;
}

function makeEvent(task: CalendarSyncTask, calendarId: string) {
  const startDate = validDate(task.due_date) ?? validDate(task.reminder_time);
  if (!startDate) return null;
  return {
    calendarId,
    title: task.title,
    notes: task.description || undefined,
    startDate,
    endDate: new Date(startDate.getTime() + 60 * 60 * 1000),
  };
}

export async function syncTaskToCalendar(task: CalendarSyncTask): Promise<string | null> {
  const key = eventKey(task.id);
  const eventId = await AsyncStorage.getItem(key);
  const calendarId = task.calendar_sync ? await getWritableCalendarId() : null;
  const event = calendarId ? makeEvent(task, calendarId) : null;
  if (!event) {
    if (eventId) await removeTaskFromCalendar(task.id);
    return null;
  }
  if (eventId) {
    try {
      await Calendar.updateEventAsync(eventId, event);
      return eventId;
    } catch {
      // Native events can be deleted outside the app; replace a stale mapping.
    }
  }
  const newEventId = await Calendar.createEventAsync(event.calendarId, event);
  await AsyncStorage.setItem(key, newEventId);
  return newEventId;
}

export async function removeTaskFromCalendar(taskId: string): Promise<void> {
  const key = eventKey(taskId);
  const eventId = await AsyncStorage.getItem(key);
  if (!eventId) return;
  try {
    // Removing a sync never prompts the user for permission.
    const { status } = await Calendar.getCalendarPermissionsAsync();
    if (status === 'granted') await Calendar.deleteEventAsync(eventId);
  } finally {
    await AsyncStorage.removeItem(key);
  }
}
