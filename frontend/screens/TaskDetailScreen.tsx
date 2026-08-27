import { useEffect, useState } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity,
  ActivityIndicator, ScrollView, Alert,
} from 'react-native';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/AppNavigator';
import { getTaskById, breakdownTask, markTaskDone, snoozeTask } from '../services/tasks';

type Nav = NativeStackNavigationProp<RootStackParamList, 'TaskDetail'>;
type Route = RouteProp<RootStackParamList, 'TaskDetail'>;

type Task = {
  id: string;
  title: string;
  priority: string;
  status: string;
  due_date?: string;
  reminder_time?: string;
};

export default function TaskDetailScreen() {
  const navigation = useNavigation<Nav>();
  const route = useRoute<Route>();
  const { taskId } = route.params;

  const [task, setTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(true);
  const [breakdownLoading, setBreakdownLoading] = useState(false);
  const [subtasks, setSubtasks] = useState<string[] | null>(null);

  async function loadTask() {
    setLoading(true);
    try {
      const data = await getTaskById(taskId);
      setTask(data);
    } catch {
      Alert.alert('Could not load task');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadTask(); }, [taskId]);

  async function handleBreakdown() {
    setBreakdownLoading(true);
    try {
      const result = await breakdownTask(taskId);
      setSubtasks(Array.isArray(result) ? result : result.subtasks);
    } catch (err: any) {
      if (err?.response?.status === 429) {
        Alert.alert('Daily AI limit reached', 'Try again tomorrow.');
      } else {
        Alert.alert('Breakdown failed', 'Something went wrong — try again.');
      }
    } finally {
      setBreakdownLoading(false);
    }
  }

  async function handleMarkDone() {
    try {
      await markTaskDone(taskId);
      const n = await import('../services/notifications').catch(() => null);
      if (n) await n.cancelTaskReminder(taskId);
      navigation.goBack();
    } catch (err) {
      console.log('handleMarkDone error:', err);
    }
  }

  async function handleSnooze() {
    try {
      const updated = await snoozeTask(taskId);
      setTask(updated);
    } catch (err) {
      console.log('handleSnooze error:', err);
    }
  }

  if (loading) {
    return <View style={styles.centered}><ActivityIndicator /></View>;
  }

  if (!task) {
    return <View style={styles.centered}><Text>Task not found.</Text></View>;
  }

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>{task.title}</Text>

      <View style={styles.row}>
        <Text style={styles.label}>Priority</Text>
        <Text style={styles.value}>{task.priority}</Text>
      </View>
      <View style={styles.row}>
        <Text style={styles.label}>Status</Text>
        <Text style={styles.value}>{task.status}</Text>
      </View>
      {task.due_date && (
        <View style={styles.row}>
          <Text style={styles.label}>Due</Text>
          <Text style={styles.value}>
            {new Date(task.due_date.endsWith('Z') ? task.due_date : task.due_date + 'Z').toLocaleDateString()}
          </Text>
        </View>
      )}
      {task.reminder_time && (
        <View style={styles.row}>
          <Text style={styles.label}>Reminder</Text>
          <Text style={styles.value}>
            {new Date(task.reminder_time.endsWith('Z') ? task.reminder_time : task.reminder_time + 'Z').toLocaleString()}
          </Text>
        </View>
      )}

      {!subtasks && (
        <TouchableOpacity
          style={styles.breakdownButton}
          onPress={handleBreakdown}
          disabled={breakdownLoading}
        >
          {breakdownLoading
            ? <ActivityIndicator color="#333" />
            : <Text style={styles.breakdownButtonText}>✨ Break down task</Text>
          }
        </TouchableOpacity>
      )}

      {subtasks && (
        <View style={styles.subtasksBox}>
          <Text style={styles.subtasksLabel}>Suggested steps</Text>
          {subtasks.map((step, i) => (
            <Text key={i} style={styles.subtaskItem}>{i + 1}. {step}</Text>
          ))}
        </View>
      )}

      <TouchableOpacity style={styles.doneButton} onPress={handleMarkDone}>
        <Text style={styles.doneButtonText}>Mark Done</Text>
      </TouchableOpacity>
      <TouchableOpacity onPress={handleSnooze}>
        <Text style={styles.snoozeLink}>Snooze</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 20, backgroundColor: '#fff' },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: { fontSize: 20, fontWeight: '700', marginBottom: 16 },
  row: {
    flexDirection: 'row', justifyContent: 'space-between',
    paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: '#eee',
  },
  label: { color: '#888' },
  value: { fontWeight: '600', textTransform: 'capitalize' },
  breakdownButton: {
    marginTop: 20, borderWidth: 1.5, borderColor: '#333',
    borderRadius: 8, padding: 12, alignItems: 'center',
  },
  breakdownButtonText: { fontWeight: '600', color: '#333' },
  subtasksBox: { marginTop: 20, backgroundColor: '#f5f5f5', borderRadius: 8, padding: 14 },
  subtasksLabel: { fontWeight: '700', marginBottom: 8 },
  subtaskItem: { marginBottom: 6, fontSize: 14 },
  doneButton: {
    marginTop: 24, backgroundColor: '#333',
    padding: 14, borderRadius: 8, alignItems: 'center',
  },
  doneButtonText: { color: '#fff', fontWeight: '600' },
  snoozeLink: { textAlign: 'center', marginTop: 12, color: '#888' },
});
