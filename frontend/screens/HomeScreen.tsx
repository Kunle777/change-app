import { useEffect, useState } from 'react';
import { View, FlatList, Text, StyleSheet, TextInput, TouchableOpacity } from 'react-native';
import TaskCard from '../components/TaskCard';
import { getTasks, createTask, markTaskDone, snoozeTask } from '../services/tasks';

type Task = {
  id: string;
  title: string;
  priority: string;
  status: string;
  due_date?: string;
};

export default function HomeScreen() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [newTitle, setnewTitle] = useState('');

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
  }, []);

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
      await createTask({ title: newTitle.trim() });
      setnewTitle('');
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
