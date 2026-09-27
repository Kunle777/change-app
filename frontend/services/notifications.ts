import * as Notifications from 'expo-notifications';
import Constants from 'expo-constants';
import * as Device from 'expo-device';
import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import type { UpcomingReminderTask } from './tasks';
import { recordTaskEvent } from './taskEvents';

const STORAGE_KEY_PREFIX = 'notif_id_for_task_';
const STORAGE_TIME_PREFIX = 'notif_time_for_task_';
const TASK_REMINDER_TYPE = 'task_reminder';
const isExpoGo = (() => {
  const constants = Constants as typeof Constants & { expoGo?: boolean };
  return (
    constants.appOwnership === 'expo' ||
    constants.executionEnvironment === 'storeClient' ||
    constants.expoGo === true
  );
})();

export async function requestNotificationPermissions(): Promise<boolean> {
  if (isExpoGo) return false;
  try {
    Notifications.setNotificationHandler({
      handleNotification: async () => ({
        shouldShowAlert: true,
        shouldPlaySound: true,
        shouldSetBadge: false,
        shouldShowBanner: true,
        shouldShowList: true,
      }),
    });
  } catch {}

  if (!Device.isDevice) {
    console.error('Push notifications only work on physical devices');
    return false;
  }

  const { status: existingStatus } = await Notifications.getPermissionsAsync();
  let finalStatus = existingStatus;

  if (existingStatus !== 'granted') {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }

  if (finalStatus !== 'granted') {
    console.log('Notification permission denied');
    return false;
  }

  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('default', {
      name: 'default',
      importance: Notifications.AndroidImportance.HIGH,
      vibrationPattern: [0, 250, 250, 250],
    });
  }

  return true;
}

export async function scheduleTaskReminder(
  taskId: string,
  title: string,
  reminderDate: Date,
): Promise<string | null> {
  if (isExpoGo || Platform.OS === 'web' || !Device.isDevice) return null;
  if (!(reminderDate instanceof Date) || !Number.isFinite(reminderDate.getTime())) return null;
  if (reminderDate.getTime() <= Date.now()) return null;

  const permissionGranted = await requestNotificationPermissions();
  if (!permissionGranted) return null;

  const notificationId = await Notifications.scheduleNotificationAsync({
    content: {
      title: 'Task Reminder',
      body: title,
      sound: true,
      data: { type: TASK_REMINDER_TYPE, taskId, reminderTime: reminderDate.toISOString() },
    },
    trigger: {
      type: Notifications.SchedulableTriggerInputTypes.DATE,
      date: reminderDate,
    },
  });

  await AsyncStorage.multiSet([
    [STORAGE_KEY_PREFIX + taskId, notificationId],
    [STORAGE_TIME_PREFIX + taskId, reminderDate.toISOString()],
  ]);
  void recordTaskEvent(taskId, 'reminder_scheduled', reminderDate.toISOString(), notificationId);
  return notificationId;
}

export async function cancelTaskReminder(taskId: string): Promise<void> {
  if (isExpoGo) return;
  const notificationId = await AsyncStorage.getItem(STORAGE_KEY_PREFIX + taskId);
  try {
    const scheduled = await Notifications.getAllScheduledNotificationsAsync();
    const ownedIds = scheduled
      .filter((notification) =>
        notification.content.data?.type === TASK_REMINDER_TYPE &&
        notification.content.data?.taskId === taskId,
      )
      .map((notification) => notification.identifier);
    const ids = new Set([...ownedIds, ...(notificationId ? [notificationId] : [])]);
    await Promise.allSettled([...ids].map((id) => Notifications.cancelScheduledNotificationAsync(id)));
  } finally {
    await AsyncStorage.multiRemove([
      STORAGE_KEY_PREFIX + taskId,
      STORAGE_TIME_PREFIX + taskId,
    ]);
  }
}

export async function rescheduleTaskReminder(
  taskId: string,
  title: string,
  newReminderDate: Date,
): Promise<string | null> {
  await cancelTaskReminder(taskId);
  return scheduleTaskReminder(taskId, title, newReminderDate);
}

let reconciliation: Promise<void> | null = null;

export function reconcileNotifications(): Promise<void> {
  if (isExpoGo) return Promise.resolve();
  if (reconciliation) return reconciliation;
  reconciliation = reconcileTaskReminders().finally(() => {
    reconciliation = null;
  });
  return reconciliation;
}

export async function clearTaskReminders(): Promise<void> {
  if (isExpoGo) return;
  try {
    const keys = await AsyncStorage.getAllKeys();
    const idKeys = keys.filter((key) => key.startsWith(STORAGE_KEY_PREFIX));
    const timeKeys = keys.filter((key) => key.startsWith(STORAGE_TIME_PREFIX));
    const scheduled = await Notifications.getAllScheduledNotificationsAsync();
    const scheduledIds = new Set(scheduled.map((notification) => notification.identifier));
    const ownedIds = scheduled
      .filter((notification) => notification.content.data?.type === TASK_REMINDER_TYPE)
      .map((notification) => notification.identifier);
    const ids = await AsyncStorage.multiGet(idKeys);
    const mappedIds = ids
      .map(([, id]) => id)
      .filter((id): id is string => Boolean(id && scheduledIds.has(id)));
    const allTaskReminderIds = new Set([...ownedIds, ...mappedIds]);
    await Promise.allSettled(
      [...allTaskReminderIds].map((id) => Notifications.cancelScheduledNotificationAsync(id)),
    );
    await AsyncStorage.multiRemove([...idKeys, ...timeKeys]);
  } catch (error) {
    console.warn('Could not clear reminders after sign-out', error);
  }
}

async function reconcileTaskReminders() {
  try {
    const { getUpcomingTasks } = await import('./tasks');
    const upcoming = await getUpcomingTasks(14);
    const tasksById = new Map(upcoming.map((task: UpcomingReminderTask) => [task.id, task]));
    const scheduled = await Notifications.getAllScheduledNotificationsAsync();
    const scheduledIds = new Set(scheduled.map((notification) => notification.identifier));
    const taggedByTaskId = new Map<string, typeof scheduled>();
    for (const notification of scheduled) {
      const data = notification.content.data;
      if (data?.type !== TASK_REMINDER_TYPE || typeof data.taskId !== 'string') continue;
      const taskNotifications = taggedByTaskId.get(data.taskId) ?? [];
      taskNotifications.push(notification);
      taggedByTaskId.set(data.taskId, taskNotifications);
    }
    const keys = await AsyncStorage.getAllKeys();
    const reminderKeys = keys.filter((key) => key.startsWith(STORAGE_KEY_PREFIX));
    const now = Date.now();
    const horizon = now + 14 * 24 * 60 * 60 * 1000;
    const localTaskIds = new Set(reminderKeys.map((key) => key.slice(STORAGE_KEY_PREFIX.length)));

    const cancelKnownTaskNotifications = async (ids: string[]) => {
      await Promise.allSettled(
        [...new Set(ids)].filter((id) => scheduledIds.has(id))
          .map((id) => Notifications.cancelScheduledNotificationAsync(id)),
      );
    };

    for (const task of upcoming) {
      if (!task.reminder_time) {
        const storedId = await AsyncStorage.getItem(STORAGE_KEY_PREFIX + task.id);
        await cancelKnownTaskNotifications([
          ...(taggedByTaskId.get(task.id) ?? []).map((notification) => notification.identifier),
          ...(storedId ? [storedId] : []),
        ]);
        await AsyncStorage.multiRemove([
          STORAGE_KEY_PREFIX + task.id,
          STORAGE_TIME_PREFIX + task.id,
        ]);
        continue;
      }
      const currentTimestamp = Date.parse(task.reminder_time);
      if (!Number.isFinite(currentTimestamp)) continue;

      const key = STORAGE_KEY_PREFIX + task.id;
      const timeKey = STORAGE_TIME_PREFIX + task.id;
      const [storedId, savedTime] = await Promise.all([
        AsyncStorage.getItem(key),
        AsyncStorage.getItem(timeKey),
      ]);
      const savedTimestamp = savedTime ? Date.parse(savedTime) : Number.NaN;
      const taskNotifications = taggedByTaskId.get(task.id) ?? [];
      const matchingNotification = taskNotifications.find((notification) => {
        const scheduledTime = notification.content.data?.reminderTime;
        return typeof scheduledTime === 'string' && Date.parse(scheduledTime) === currentTimestamp;
      }) ?? taskNotifications.find((notification) =>
        notification.identifier === storedId && savedTimestamp === currentTimestamp,
      );

      if (matchingNotification) {
        const duplicates = taskNotifications
          .filter((notification) => notification.identifier !== matchingNotification.identifier)
          .map((notification) => notification.identifier);
        await cancelKnownTaskNotifications(duplicates);
        await AsyncStorage.multiSet([
          [key, matchingNotification.identifier],
          [timeKey, task.reminder_time],
        ]);
        continue;
      }

      await cancelKnownTaskNotifications([
        ...taskNotifications.map((notification) => notification.identifier),
        ...(storedId ? [storedId] : []),
      ]);
      await AsyncStorage.multiRemove([key, timeKey]);
      await scheduleTaskReminder(task.id, task.title, new Date(currentTimestamp));
    }

    for (const key of reminderKeys) {
      const taskId = key.slice(STORAGE_KEY_PREFIX.length);
      if (tasksById.has(taskId)) continue;

      const timeKey = STORAGE_TIME_PREFIX + taskId;
      const [storedId, savedTime] = await Promise.all([
        AsyncStorage.getItem(key),
        AsyncStorage.getItem(timeKey),
      ]);
      const taskNotifications = taggedByTaskId.get(taskId) ?? [];
      const storedTimestamp = savedTime ? Date.parse(savedTime) : Number.NaN;
      const taggedTimestamp = taskNotifications
        .map(getTaskReminderTimestamp)
        .find((timestamp) => Number.isFinite(timestamp));
      const reminderTimestamp = Number.isFinite(storedTimestamp) ? storedTimestamp : taggedTimestamp;

      // Leave far-future reminders intact; stale/in-window task reminders for
      // tasks the API no longer returns are removed during this sync.
      if (!Number.isFinite(reminderTimestamp) || reminderTimestamp! <= horizon) {
        await cancelKnownTaskNotifications([
          ...taskNotifications.map((notification) => notification.identifier),
          ...(storedId ? [storedId] : []),
        ]);
        await AsyncStorage.multiRemove([key, timeKey]);
      }
    }

    // Also catch tagged reminders whose AsyncStorage mapping was lost. A
    // notification without our explicit type tag is never canceled here.
    for (const [taskId, taskNotifications] of taggedByTaskId) {
      if (tasksById.has(taskId) || localTaskIds.has(taskId)) continue;
      const timestamps = taskNotifications.map(getTaskReminderTimestamp);
      if (timestamps.some((timestamp) => Number.isFinite(timestamp) && timestamp > horizon)) continue;
      await cancelKnownTaskNotifications(taskNotifications.map((notification) => notification.identifier));
    }
  } catch (error) {
    console.warn('Notification reconciliation failed:', error);
  }
}

function getTaskReminderTimestamp(notification: Notifications.NotificationRequest): number {
  const reminderTime = notification.content.data?.reminderTime;
  if (typeof reminderTime === 'string') return Date.parse(reminderTime);

  const trigger = notification.trigger as unknown as { date?: string | number | Date; value?: string | number | Date };
  const value = trigger.date ?? trigger.value;
  if (value instanceof Date) return value.getTime();
  if (typeof value === 'number') return value;
  if (typeof value === 'string') return Date.parse(value);
  return Number.NaN;
}
