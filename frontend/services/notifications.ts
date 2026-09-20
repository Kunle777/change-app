import * as Device from 'expo-device';
import Constants from 'expo-constants';
import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

const STORAGE_KEY_PREFIX = 'notif_id_for_task_';
const isExpoGo = (() => {
  const constants = Constants as typeof Constants & {
    expoGo?: boolean;
  };
  return (
    constants.appOwnership === 'expo' ||
    constants.executionEnvironment === 'storeClient' ||
    constants.expoGo === true
  );
})();

export async function requestNotificationPermissions(): Promise<boolean> {
  if (isExpoGo) return false;

  try {
    const Notifications = await import('expo-notifications');
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

  const Notifications = await import('expo-notifications');
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
    const Notifications = await import('expo-notifications');
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

  const Notifications = await import('expo-notifications');
  const notificationId = await Notifications.scheduleNotificationAsync({
    content: {
      title: 'Task Reminder',
      body: title,
      sound: true,
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
  if (isExpoGo) return;

  const notificationId = await AsyncStorage.getItem(STORAGE_KEY_PREFIX + taskId);
  if (notificationId) {
    const Notifications = await import('expo-notifications');
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
