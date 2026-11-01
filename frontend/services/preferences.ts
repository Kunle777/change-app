import AsyncStorage from '@react-native-async-storage/async-storage';

// Same key the old Settings screen used, so an existing choice carries over.
const DEFAULT_PRIORITY_KEY = 'settings_default_priority';

export async function getDefaultPriorityReminder(): Promise<boolean> {
  try {
    const raw = await AsyncStorage.getItem(DEFAULT_PRIORITY_KEY);
    return raw !== null && JSON.parse(raw) === true;
  } catch {
    return false;
  }
}

export async function setDefaultPriorityReminder(value: boolean): Promise<void> {
  await AsyncStorage.setItem(DEFAULT_PRIORITY_KEY, JSON.stringify(value));
}
