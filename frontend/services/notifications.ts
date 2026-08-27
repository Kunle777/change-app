import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

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
): Promise<string | null> {
  if (reminderDate.getTime() <= Date.now()) return null;

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
