import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { getTasks } from './tasks';

const STORAGE_KEY_PREFIX = 'notif_id_for_task_';

export async function requestNotificationPermissions(): Promise<boolean> {
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
  priorityReminder = false,
): Promise<string | null> {
  if (Platform.OS === 'web' || !Device.isDevice) return null;
  if (!(reminderDate instanceof Date) || !Number.isFinite(reminderDate.getTime())) return null;
  if (reminderDate.getTime() <= Date.now()) return null;

  const permissionGranted = await requestNotificationPermissions();
  if (!permissionGranted) return null;

  const notificationId = await Notifications.scheduleNotificationAsync({
    content: {
      title: priorityReminder ? 'Priority task reminder' : 'Task reminder',
      body: title,
      sound: true,
      data: { type: 'task_reminder', taskId },
    },
    trigger: {
      type: Notifications.SchedulableTriggerInputTypes.DATE,
      date: reminderDate,
    },
  });

  await AsyncStorage.setItem(STORAGE_KEY_PREFIX + taskId, notificationId);
  return notificationId;
}

export async function cancelTaskReminder(taskId: string): Promise<void> {
  const notificationId = await AsyncStorage.getItem(STORAGE_KEY_PREFIX + taskId);
  if (notificationId) {
    await Notifications.cancelScheduledNotificationAsync(notificationId);
    await AsyncStorage.removeItem(STORAGE_KEY_PREFIX + taskId);
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

export async function clearTaskReminders(): Promise<void> {
  const keys = (await AsyncStorage.getAllKeys()).filter((key) =>
    key.startsWith(STORAGE_KEY_PREFIX),
  );
  const entries = await AsyncStorage.multiGet(keys);
  await Promise.allSettled(
    entries
      .map(([, notificationId]) => notificationId)
      .filter((notificationId): notificationId is string => Boolean(notificationId))
      .map((notificationId) => Notifications.cancelScheduledNotificationAsync(notificationId)),
  );
  if (keys.length) await AsyncStorage.multiRemove(keys);
}

type ReminderTask = {
  id: string;
  title: string;
  reminder_time?: string | null;
  status?: string | null;
  is_deleted?: boolean;
};

export async function reconcileNotifications(): Promise<void> {
  if (Platform.OS === 'web' || !Device.isDevice) return;

  const tasks = (await getTasks()) as ReminderTask[];
  const activeTasks = tasks.filter(
    (task) =>
      !task.is_deleted &&
      task.status !== 'completed' &&
      task.status !== 'cancelled' &&
      Boolean(task.reminder_time),
  );
  const activeIds = new Set(activeTasks.map((task) => task.id));
  const storedKeys = (await AsyncStorage.getAllKeys()).filter((key) =>
    key.startsWith(STORAGE_KEY_PREFIX),
  );
  const staleIds = storedKeys
    .map((key) => key.slice(STORAGE_KEY_PREFIX.length))
    .filter((taskId) => !activeIds.has(taskId));

  await Promise.all(staleIds.map((taskId) => cancelTaskReminder(taskId)));
  await Promise.all(
    activeTasks.map(async (task) => {
      const reminderDate = task.reminder_time ? new Date(task.reminder_time) : null;
      if (!reminderDate || !Number.isFinite(reminderDate.getTime())) {
        await cancelTaskReminder(task.id);
        return;
      }
      await rescheduleTaskReminder(task.id, task.title, reminderDate);
    }),
  );
}
