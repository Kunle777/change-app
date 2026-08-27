import { useEffect, useState, useCallback } from 'react';
import {
  Platform,
  AppState,
  View,
  FlatList,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  RefreshControl,
} from 'react-native';
import DateTimePicker, { DateTimePickerEvent } from '@react-native-community/datetimepicker';
import { useNavigation } from '@react-navigation/native';
import { useFocusEffect } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList, MainTabParamList } from '../navigation/AppNavigator';
import WinLogScreen from './WinLogScreen';

type Nav = NativeStackNavigationProp<
  RootStackParamList & { [K in keyof MainTabParamList]: MainTabParamList[K] }
>;
import TaskCard from '../components/TaskCard';
import { getTasks, createTask, markTaskDone, snoozeTask } from '../services/tasks';
import { updateFcmToken } from '../services/auth';
import { getTodayCheckinStatus } from '../services/checkins';
import { supabase } from '../services/supabase';

type Task = {
  id: string;
  title: string;
  priority: string;
  status: string;
  due_date?: string;
  reminder_time?: string;
};

type CheckinStatus = {
  checkins_enabled: boolean;
  morning_done: boolean;
  evening_done: boolean;
} | null;

export default function HomeScreen() {
  const navigation = useNavigation<Nav>();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [newTitle, setnewTitle] = useState('');
  const [reminderDate, setReminderDate] = useState<Date | null>(null);
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [showTimePicker, setShowTimePicker] = useState(false);
  const [checkinStatus, setCheckinStatus] = useState<CheckinStatus>(null);
  const [now, setNow] = useState(new Date());

  const hour = now.getHours();

  const loadTasks = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getTasks();
      setTasks(data);
    } catch (err) {
      console.log('loadTasks error:', err);
      if (
        (err instanceof Error && err.message.includes('Please log in again')) ||
        (err as any)?.response?.status === 401
      ) {
        await supabase.auth.signOut();
        navigation.reset({ index: 0, routes: [{ name: 'Login' }] });
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      loadTasks();
    }, []),
  );

  useEffect(() => {
    registerForPushNotification();
    import('../services/notifications')
      .then((n) => n.requestNotificationPermissions())
      .catch(() => {});

    let isMounted = true;
    getTodayCheckinStatus()
      .then((data) => {
        if (isMounted) setCheckinStatus(data);
      })
      .catch(() => {
        if (isMounted)
          setCheckinStatus({ checkins_enabled: false, morning_done: false, evening_done: false });
      });

    const subscription = AppState.addEventListener('change', (state) => {
      if (state === 'active') setNow(new Date());
    });

    return () => {
      isMounted = false;
      subscription.remove();
    };
  }, []);

  async function registerForPushNotification() {
    if (Platform.OS === 'web') return;
    try {
      const messagingModule = await import('@react-native-firebase/messaging');
      const messaging = messagingModule.default;
      if (!messaging || typeof messaging !== 'function') return;
      const instance = messaging();
      const authStatus = await instance.requestPermission();
      const enabled =
        authStatus === (messaging as any).AuthorizationStatus?.AUTHORIZED ||
        authStatus === (messaging as any).AuthorizationStatus?.PROVISIONAL;
      if (!enabled) return;
      const token = await instance.getToken();
      if (token) await updateFcmToken(token);
    } catch {
      // silently skip in Expo Go — Firebase requires a native build
    }
  }

  async function handleDone(taskId: string) {
    try {
      await markTaskDone(taskId);
      const n = await import('../services/notifications').catch(() => null);
      if (n && typeof n.cancelTaskReminder === 'function') await n.cancelTaskReminder(taskId);
      setTasks((prev) => prev.filter((t) => t.id !== taskId));
    } catch (err) {
      console.log('handleDone error:', err);
    }
  }

  async function handleSnooze(taskId: string) {
    try {
      const updatedTask = await snoozeTask(taskId);
      if (updatedTask?.reminder_time) {
        const n = await import('../services/notifications').catch(() => null);
        if (n && typeof n.rescheduleTaskReminder === 'function')
          await n.rescheduleTaskReminder(
            taskId,
            updatedTask.title,
            new Date(updatedTask.reminder_time),
          );
      }
      setTasks((prev) => prev.map((t) => (t.id === taskId ? { ...t, ...updatedTask } : t)));
    } catch (err) {
      console.log('handleSnooze error:', err);
    }
  }

  async function handleCreateTask() {
    if (!newTitle.trim()) return;
    let reminder_time: string | undefined;
    let due_date: string | undefined;
    if (reminderDate) {
      const iso = reminderDate.toISOString();
      reminder_time = iso;
      due_date = iso.split('T')[0] + 'T00:00:00';
    }
    try {
      const createdTask = await createTask({
        title: newTitle.trim(),
        ...(reminder_time ? { reminder_time } : {}),
        ...(due_date ? { due_date } : {}),
      });
      if (reminder_time && createdTask?.id) {
        const n = await import('../services/notifications').catch(() => null);
        if (n && typeof n.scheduleTaskReminder === 'function')
          await n.scheduleTaskReminder(createdTask.id, createdTask.title, new Date(reminder_time));
      }
      setnewTitle('');
      setReminderDate(null);
      loadTasks();
    } catch (err) {
      console.log('createTask error:', err);
    }
  }

  if (loading) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
        <Text>Loading...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {checkinStatus?.checkins_enabled && (
        <TouchableOpacity
          style={styles.persistentCheckinIcon}
          onPress={() =>
            navigation.navigate('CheckIn', { type: hour < 12 ? 'morning' : 'evening' })
          }
        >
          <Text style={styles.persistentCheckinIconText}>{hour < 12 ? '🌅' : '🌙'} Check In</Text>
        </TouchableOpacity>
      )}
      {checkinStatus?.checkins_enabled && !checkinStatus.morning_done && hour < 12 && (
        <TouchableOpacity
          style={styles.banner}
          onPress={() => navigation.navigate('CheckIn', { type: 'morning' })}
        >
          <Text style={styles.bannerText}>🌅 Morning check-in ready — tap to start</Text>
          <TouchableOpacity
            onPress={() => setCheckinStatus({ ...checkinStatus, morning_done: true })}
          >
            <Text style={styles.bannerDismiss}>✕</Text>
          </TouchableOpacity>
        </TouchableOpacity>
      )}
      {checkinStatus?.checkins_enabled && !checkinStatus.evening_done && hour >= 12 && (
        <TouchableOpacity
          style={[styles.banner, styles.bannerEvening]}
          onPress={() => navigation.navigate('CheckIn', { type: 'evening' })}
        >
          <Text style={styles.bannerText}>🌙 Evening check-in ready — tap to start</Text>
          <TouchableOpacity
            onPress={() => setCheckinStatus({ ...checkinStatus, evening_done: true })}
          >
            <Text style={styles.bannerDismiss}>✕</Text>
          </TouchableOpacity>
        </TouchableOpacity>
      )}

      <TextInput
        style={styles.input}
        placeholder="New task.."
        value={newTitle}
        onChangeText={setnewTitle}
        placeholderTextColor="#999"
      />
      <TouchableOpacity style={styles.datePickerButton} onPress={() => setShowDatePicker(true)}>
        <Text style={styles.datePickerText}>
          {reminderDate ? `📅 ${reminderDate.toLocaleDateString()}` : '📅 Set date (optional)'}
        </Text>
      </TouchableOpacity>
      {reminderDate && (
        <TouchableOpacity style={styles.datePickerButton} onPress={() => setShowTimePicker(true)}>
          <Text style={styles.datePickerText}>
            {`⏰ ${reminderDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`}
          </Text>
        </TouchableOpacity>
      )}
      {reminderDate && (
        <TouchableOpacity onPress={() => setReminderDate(null)}>
          <Text style={styles.clearDate}>✕ Clear date</Text>
        </TouchableOpacity>
      )}
      {showDatePicker && (
        <DateTimePicker
          value={reminderDate || new Date()}
          mode="date"
          display={Platform.OS === 'ios' ? 'spinner' : 'default'}
          minimumDate={new Date()}
          onChange={(e: DateTimePickerEvent, date?: Date) => {
            setShowDatePicker(false);
            if (e.type === 'set' && date) {
              setReminderDate((prev) => {
                const base = prev || new Date();
                date.setHours(base.getHours(), base.getMinutes());
                return date;
              });
            }
          }}
        />
      )}
      {showTimePicker && (
        <DateTimePicker
          value={reminderDate || new Date()}
          mode="time"
          display={Platform.OS === 'ios' ? 'spinner' : 'default'}
          onChange={(e: DateTimePickerEvent, time?: Date) => {
            setShowTimePicker(false);
            if (e.type === 'set' && time && reminderDate) {
              const updated = new Date(reminderDate);
              updated.setHours(time.getHours(), time.getMinutes());
              setReminderDate(updated);
            }
          }}
        />
      )}
      <TouchableOpacity onPress={handleCreateTask} style={styles.addButton}>
        <Text style={styles.addButtonText}>Add Task</Text>
      </TouchableOpacity>

      <View style={styles.checkinRow}>
        <TouchableOpacity
          style={styles.checkinButton}
          onPress={() => navigation.navigate('CheckIn', { type: 'morning' })}
        >
          <Text style={styles.checkinButtonText}>Morning Check-in</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.checkinButton}
          onPress={() => navigation.navigate('CheckIn', { type: 'evening' })}
        >
          <Text style={styles.checkinButtonText}>Evening Check-in</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.calendarButton}
          onPress={() => navigation.navigate('Calendar')}
        >
          <Text style={styles.calendarButtonText}>📅 Calendar</Text>
        </TouchableOpacity>
      </View>
      <TouchableOpacity onPress={() => navigation.navigate('WinLog')}>
        <Text style={styles.winLogLink}>🏆 Win Log</Text>
      </TouchableOpacity>
      <Text style={styles.sectionTitle}>My Tasks</Text>
      <FlatList
        data={tasks}
        keyExtractor={(item) => item.id}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={loadTasks} />}
        renderItem={({ item }) => (
          <TouchableOpacity onPress={() => navigation.navigate('TaskDetail', { taskId: item.id })}>
            <TaskCard
              task={item}
              onDone={() => handleDone(item.id)}
              onSnooze={() => handleSnooze(item.id)}
            />
          </TouchableOpacity>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 20, backgroundColor: '#f5f5f5' },
  input: {
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
    backgroundColor: '#fff',
  },
  datePickerButton: {
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
    backgroundColor: '#fff',
  },
  datePickerText: { color: '#333' },
  clearDate: { color: '#888', fontSize: 12, marginBottom: 8, textAlign: 'right' },
  addButton: {
    backgroundColor: '#007bff',
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
    marginBottom: 12,
  },
  addButtonText: { color: '#fff', fontWeight: '600' },
  checkinRow: { flexDirection: 'row', gap: 8, marginBottom: 16 },
  checkinButton: {
    flex: 1,
    backgroundColor: '#28a745',
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  checkinButtonText: { color: '#fff', fontWeight: '600' },
  aiButton: {
    backgroundColor: '#6f42c1',
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
    marginBottom: 16,
  },
  aiButtonText: { color: '#fff', fontWeight: '600' },
  brainDumpButton: {
    backgroundColor: '#e67e22',
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
    marginBottom: 16,
  },
  brainDumpButtonText: { color: '#fff', fontWeight: '600' },
  settingsButton: {
    backgroundColor: '#6c757d',
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
    marginBottom: 16,
  },
  settingsButtonText: { color: '#fff', fontWeight: '600' },
  sectionTitle: { textAlign: 'center', fontWeight: 'bold', fontSize: 18, marginBottom: 8 },
  banner: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#fff3cd',
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
  },
  bannerEvening: { backgroundColor: '#d1ecf1' },
  bannerText: { flex: 1, fontSize: 13, color: '#333' },
  bannerDismiss: { fontSize: 16, color: '#888', paddingLeft: 8 },
  calendarButton: {
    backgroundColor: '#fff',
    borderWidth: 1.5,
    borderColor: '#333',
    padding: 10,
    borderRadius: 8,
    alignItems: 'center',
    marginBottom: 12,
  },
  calendarButtonText: { color: '#333', fontWeight: '600' },
  persistentCheckinIcon: {
    alignSelf: 'flex-end',
    backgroundColor: '#eee',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    marginBottom: 8,
  },
  persistentCheckinIconText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#333',
  },
  winLogLink: { textAlign: 'center', color: '#333', marginBottom: 16, fontWeight: '600' },
});
