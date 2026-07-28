import { useEffect, useState } from 'react';
import { View, FlatList, Text, StyleSheet, TextInput, TouchableOpacity } from 'react-native';
import TaskCard from '../components/TaskCard';
import { getTasks, createTask, markTaskDone, snoozeTask } from '../services/tasks';
import { updateFcmToken } from '../services/auth';
import messaging from '@react-native-firebase/messaging';

type Task = {
  id: string;
  title: string;
  priority: string;
  status: string;
  due_date?: string;
  reminder_time?: string;
};

export default function HomeScreen() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [newTitle, setnewTitle] = useState('');
  const [newReminderTime, setNewReminderTime] = useState('');

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
  }, []);

  async function registerForPushNotification() {
    const authStatus = await messaging().requestPermission();
    const enabled =
      authStatus === messaging.AuthorizationStatus.AUTHORIZED ||
      authStatus === messaging.AuthorizationStatus.PROVISIONAL;

    if (!enabled) {
      console.log('Push notifications permission not granted', authStatus);
      return;
    }

    try {
      const token = await messaging().getToken();
      if (token) {
        await updateFcmToken(token);
        console.log('FCM token registered:', token);
      }
    } catch (err) {
      console.log('registerForPushNotification error:', err);
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
    try {
      await createTask({
        title: newTitle.trim(),
        reminder_time: newReminderTime ? newReminderTime : undefined,
      });
      setnewTitle('');
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
      <TextInput
        style={styles.input}
        placeholder="New task.."
        value={newTitle}
        onChangeText={setnewTitle}
      />
      <TextInput
        style={styles.input}
        placeholder="Reminder time (YYYY-MM-DDTHH:MM)"
        value={newReminderTime}
        onChangeText={setNewReminderTime}
      />
      <TouchableOpacity onPress={handleCreateTask} style={styles.addButton}>
        <Text>Add Task</Text>
      </TouchableOpacity>
      <Text style={{ textAlign: 'center', fontWeight: 'bold', fontSize: 20 }}>Create Task</Text>
      <Text style={{ textAlign: 'center', fontWeight: 'bold', fontSize: 20 }}>My Tasks</Text>
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
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: '#f5f5f5',
  },
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
    marginBottom: 16,
  },
});
