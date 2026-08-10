import { useEffect, useState } from 'react';
import {
  Platform,
  View,
  FlatList,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/AppNavigator';
import TaskCard from '../components/TaskCard';
import { getTasks, createTask, markTaskDone, snoozeTask } from '../services/tasks';
import { updateFcmToken } from '../services/auth';
import { getTodayCheckinStatus } from '../services/checkins';

type Nav = NativeStackNavigationProp<RootStackParamList, 'Home'>;

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
  const [newReminderDate, setNewReminderDate] = useState('');
  const [newReminderTime, setNewReminderTime] = useState('');
  const [checkinStatus, setCheckinStatus] = useState<CheckinStatus>(null);

  const hour = new Date().getHours();

  async function loadTasks() {
    setLoading(true);
    try {
      const data = await getTasks();
      setTasks(data);
    } catch (err) {
      console.log('loadTasks error:', err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadTasks();
    registerForPushNotification();
    getTodayCheckinStatus().then(setCheckinStatus).catch(() => {});
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
    await markTaskDone(taskId);
    loadTasks();
  }

  async function handleSnooze(taskId: string) {
    await snoozeTask(taskId);
    loadTasks();
  }

  async function handleCreateTask() {
    if (!newTitle.trim()) return;
    let reminder_time;
    if (newReminderDate && newReminderTime) {
      reminder_time = `${newReminderDate}T${newReminderTime}:00`;
    }
    try {
      await createTask({ title: newTitle.trim(), reminder_time });
      setnewTitle('');
      setNewReminderDate('');
      setNewReminderTime('');
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
      {checkinStatus?.checkins_enabled && !checkinStatus.morning_done && hour < 12 && (
        <TouchableOpacity
          style={styles.banner}
          onPress={() => navigation.navigate('CheckIn', { type: 'morning' })}
        >
          <Text style={styles.bannerText}>🌅 Morning check-in ready — tap to start</Text>
          <TouchableOpacity onPress={() => setCheckinStatus({ ...checkinStatus, morning_done: true })}>
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
          <TouchableOpacity onPress={() => setCheckinStatus({ ...checkinStatus, evening_done: true })}>
            <Text style={styles.bannerDismiss}>✕</Text>
          </TouchableOpacity>
        </TouchableOpacity>
      )}

      <TextInput
        style={styles.input}
        placeholder="New task.."
        value={newTitle}
        onChangeText={setnewTitle}
      />
      <TextInput
        style={styles.input}
        placeholder="Reminder date (YYYY-MM-DD)"
        value={newReminderDate}
        onChangeText={setNewReminderDate}
      />
      <TextInput
        style={styles.input}
        placeholder="Reminder time (HH:MM)"
        value={newReminderTime}
        onChangeText={setNewReminderTime}
      />
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
      </View>
      <TouchableOpacity
        style={styles.aiButton}
        onPress={() => navigation.navigate('AI')}
      >
        <Text style={styles.aiButtonText}>🤖 AI Assistant</Text>
      </TouchableOpacity>
      <TouchableOpacity
        style={styles.brainDumpButton}
        onPress={() => navigation.navigate('BrainDump')}
      >
        <Text style={styles.brainDumpButtonText}>🧠 Brain Dump</Text>
      </TouchableOpacity>

      <Text style={styles.sectionTitle}>My Tasks</Text>
      <FlatList
        data={tasks}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <TaskCard
            task={item}
            onDone={() => handleDone(item.id)}
            onSnooze={() => handleSnooze(item.id)}
          />
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
});
