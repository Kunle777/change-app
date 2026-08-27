import { useEffect, useState, useMemo } from 'react';
import { View, Text, FlatList, StyleSheet, ActivityIndicator, TouchableOpacity } from 'react-native';
import { Calendar, DateData } from 'react-native-calendars';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/AppNavigator';
import { getTasks } from '../services/tasks';
import TaskCard from '../components/TaskCard';

type Nav = NativeStackNavigationProp<RootStackParamList, 'TaskDetail'>;

type Task = {
  id: string;
  title: string;
  priority: string;
  status: string;
  due_date?: string;
  reminder_time?: string;
};

function getTaskDateKey(task: Task): string | null {
  const raw = task.due_date || task.reminder_time;
  if (!raw) return null;
  // Normalize: if no timezone suffix, treat as UTC to match backend storage
  const normalized = raw.endsWith('Z') || raw.includes('+') ? raw : raw + 'Z';
  return new Date(normalized).toISOString().split('T')[0];
}

export default function CalendarScreen() {
  const navigation = useNavigation<Nav>();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState<string>(
    new Date().toISOString().split('T')[0], // defaults to today, "YYYY-MM-DD"
  );

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const data = await getTasks();
        setTasks(data);
      } catch (err) {
        console.log('CalendarScreen loadTasks error:', err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  // Build the markedDates object once per tasks change, not on every render —
  // this is the actual "task list → calendar decoration" translation step.
  const markedDates = useMemo(() => {
    const marks: Record<string, any> = {};

    tasks.forEach((task) => {
      const dateKey = getTaskDateKey(task);
      if (!dateKey) return;
      marks[dateKey] = {
        ...(marks[dateKey] || {}),
        marked: true,
        dotColor: '#333',
      };
    });

    // Overlay the selected-date highlight on top of whatever dot marking
    // already exists — a date can be both "has a task" and "selected".
    marks[selectedDate] = {
      ...(marks[selectedDate] || {}),
      selected: true,
      selectedColor: '#333',
    };

    return marks;
  }, [tasks, selectedDate]);

  // Tasks due on whichever date is currently selected — recomputed
  // whenever the selection or the underlying task list changes.
  const tasksForSelectedDate = useMemo(() => {
    return tasks.filter((task) => getTaskDateKey(task) === selectedDate);
  }, [tasks, selectedDate]);

  function handleDayPress(day: DateData) {
    setSelectedDate(day.dateString);
  }

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Calendar
        current={selectedDate}
        onDayPress={handleDayPress}
        markedDates={markedDates}
        theme={{
          selectedDayBackgroundColor: '#333',
          todayTextColor: '#333',
          arrowColor: '#333',
          dotColor: '#333',
        }}
      />

      <Text style={styles.sectionLabel}>Tasks for {selectedDate}</Text>

      <FlatList
        data={tasksForSelectedDate}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <TouchableOpacity onPress={() => navigation.navigate('TaskDetail', { taskId: item.id })}>
            <TaskCard task={item} />
          </TouchableOpacity>
        )}
        ListEmptyComponent={<Text style={styles.emptyText}>No tasks due this day.</Text>}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  sectionLabel: {
    fontWeight: '700',
    fontSize: 15,
    padding: 16,
    paddingBottom: 8,
  },
  emptyText: {
    textAlign: 'center',
    color: '#999',
    marginTop: 20,
  },
});
