import { useState, useEffect, useCallback, useRef } from 'react';
import { useFocusEffect } from '@react-navigation/native';
import { View, Text, TouchableOpacity, FlatList, Modal } from 'react-native';
import { Calendar, DateData } from 'react-native-calendars';
import TaskRow from '../components/tasks/TaskRow';
import TaskActionsHost from '../components/tasks/TaskActionsHost';
import { useTaskCompletion } from '../hooks/useTaskCompletion';
import { localDateString } from '../utils/localDate';
import { getCalendarDates, getTasksByDate } from '../services/tasks';
import { Task } from '../types/task';

const FILTERS = ['all', 'incomplete', 'completed', 'overdue'] as const;
type Filter = (typeof FILTERS)[number];

const FILTER_LABELS: Record<Filter, string> = {
  all: 'All',
  incomplete: 'Incomplete',
  completed: 'Completed',
  overdue: 'Overdue',
};

export default function CalendarScreen({ navigation }: any) {
  const today = new Date();
  const [selectedDate, setSelectedDate] = useState(localDateString(today));
  const [visibleMonth, setVisibleMonth] = useState({
    year: today.getFullYear(),
    month: today.getMonth() + 1,
  });
  const [markedDates, setMarkedDates] = useState<Record<string, any>>({});
  const [tasks, setTasks] = useState<Task[]>([]);
  const [filter, setFilter] = useState<Filter>('all');
  const [showFilterMenu, setShowFilterMenu] = useState(false);

  const [activeTask, setActiveTask] = useState<Task | null>(null);

  const loadMonthDots = useCallback(async () => {
    try {
      const dates = await getCalendarDates(visibleMonth.year, visibleMonth.month);
      const marks: Record<string, any> = {};
      dates.forEach((d) => {
        marks[d] = { marked: true, dotColor: '#4F46E5' };
      });
      marks[selectedDate] = {
        ...(marks[selectedDate] ?? {}),
        selected: true,
        selectedColor: '#4F46E5',
      };
      setMarkedDates(marks);
    } catch (err) {
      console.log('Failed to load calendar dots:', err);
    }
  }, [visibleMonth, selectedDate]);

  const requestId = useRef(0);
  const loadTasksForDate = useCallback(async () => {
    const id = ++requestId.current;
    try {
      const result = await getTasksByDate(selectedDate, filter);
      if (id !== requestId.current) return; // a newer date/filter request won
      setTasks(result);
    } catch (err) {
      console.log('Failed to load tasks for date:', err);
    }
  }, [selectedDate, filter]);

  useEffect(() => {
    loadMonthDots();
  }, [loadMonthDots]);

  useEffect(() => {
    loadTasksForDate();
  }, [loadTasksForDate]);

  const refresh = useCallback(() => {
    loadTasksForDate();
    loadMonthDots();
  }, [loadTasksForDate, loadMonthDots]);

  // Pick up changes made on Home / Task Detail when returning to this screen.
  useFocusEffect(
    useCallback(() => {
      refresh();
    }, [refresh]),
  );

  const completeOptimistically = useTaskCompletion([setTasks], refresh);

  const incompleteTasks = tasks.filter((t) => t.status !== 'completed');
  const completedTasks = tasks.filter((t) => t.status === 'completed');

  const selectedDateLabel = new Date(selectedDate + 'T00:00:00').toLocaleDateString(undefined, {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  });

  return (
    <View style={{ flex: 1 }}>
      <View
        style={{
          flexDirection: 'row',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: 16,
        }}
      >
        <Text style={{ fontSize: 18, fontWeight: '700' }}>Calendar</Text>
        <TouchableOpacity
          onPress={() => navigation.navigate('CreateTask', { prefilledDate: selectedDate })}
        >
          <Text style={{ fontSize: 22 }}>+</Text>
        </TouchableOpacity>
      </View>

      <Calendar
        current={selectedDate}
        markedDates={markedDates}
        onDayPress={(day: DateData) => setSelectedDate(day.dateString)}
        onMonthChange={(month: DateData) =>
          setVisibleMonth({ year: month.year, month: month.month })
        }
        theme={{
          selectedDayBackgroundColor: '#4F46E5',
          todayTextColor: '#4F46E5',
          dotColor: '#4F46E5',
          arrowColor: '#4F46E5',
        }}
      />

      <View
        style={{
          flexDirection: 'row',
          justifyContent: 'space-between',
          alignItems: 'center',
          paddingHorizontal: 16,
          paddingTop: 16,
        }}
      >
        <View>
          <Text style={{ fontWeight: '600', fontSize: 15 }}>{selectedDateLabel}</Text>
          <Text style={{ color: '#888', fontSize: 12 }}>
            {tasks.length} {tasks.length === 1 ? 'task' : 'tasks'}
          </Text>
        </View>
        <TouchableOpacity onPress={() => setShowFilterMenu(true)}>
          <Text style={{ color: '#4F46E5' }}>{FILTER_LABELS[filter]} ▾</Text>
        </TouchableOpacity>
      </View>

      <Modal visible={showFilterMenu} transparent animationType="fade">
        <TouchableOpacity
          style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.2)' }}
          onPress={() => setShowFilterMenu(false)}
        >
          <View
            style={{
              marginTop: 160,
              marginRight: 16,
              marginLeft: 'auto',
              backgroundColor: '#fff',
              borderRadius: 12,
              overflow: 'hidden',
              width: 160,
            }}
          >
            {FILTERS.map((f) => (
              <TouchableOpacity
                key={f}
                onPress={() => {
                  setFilter(f);
                  setShowFilterMenu(false);
                }}
                style={{ padding: 12 }}
              >
                <Text style={{ fontWeight: f === filter ? '700' : '400' }}>{FILTER_LABELS[f]}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </TouchableOpacity>
      </Modal>

      <FlatList
        data={incompleteTasks}
        keyExtractor={(t) => t.id}
        contentContainerStyle={{ paddingHorizontal: 16, paddingTop: 8 }}
        ListEmptyComponent={
          <View style={{ alignItems: 'center', marginTop: 40 }}>
            <Text style={{ color: '#666', fontWeight: '600' }}>Nothing planned yet</Text>
            <Text style={{ color: '#999', fontSize: 12, marginTop: 4 }}>A clear day is okay.</Text>
          </View>
        }
        renderItem={({ item }) => (
          <TaskRow
            task={item}
            onPress={() => navigation.navigate('TaskDetail', { taskId: item.id })}
            onToggleComplete={() => completeOptimistically(item)}
            onMore={() => setActiveTask(item)}
          />
        )}
        ListFooterComponent={
          completedTasks.length > 0 ? (
            <View style={{ marginTop: 20 }}>
              <Text style={{ fontWeight: '600', color: '#888', marginBottom: 4 }}>Completed</Text>
              {completedTasks.map((item) => (
                <TaskRow
                  key={item.id}
                  task={item}
                  onPress={() => navigation.navigate('TaskDetail', { taskId: item.id })}
                  onToggleComplete={() => completeOptimistically(item)}
                  onMore={() => setActiveTask(item)}
                />
              ))}
            </View>
          ) : null
        }
      />

      <TaskActionsHost
        task={activeTask}
        onClose={() => setActiveTask(null)}
        onChanged={refresh}
        onMarkDone={completeOptimistically}
        navigation={navigation}
      />
    </View>
  );
}
