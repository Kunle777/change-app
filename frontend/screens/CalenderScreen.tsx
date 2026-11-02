import { useCallback, useMemo, useRef, useState } from 'react';
import { useFocusEffect } from '@react-navigation/native';
import { FlatList, Modal, Pressable, Text, TouchableOpacity, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Calendar, DateData } from 'react-native-calendars';
import { Ionicons } from '@expo/vector-icons';
import TaskRow from '../components/tasks/TaskRow';
import TaskActionsHost from '../components/tasks/TaskActionsHost';
import { getCalendarDates, getTasksByDate } from '../services/tasks';
import { useTaskCompletion } from '../hooks/useTaskCompletion';
import { useColors } from '../theme/colors';
import { useTheme } from '../contexts/ThemeContext';
import { localDateString } from '../utils/localDate';
import type { Task } from '../types/task';

const FILTERS = ['all', 'incomplete', 'completed', 'overdue'] as const;
type Filter = (typeof FILTERS)[number];
const FILTER_LABELS: Record<Filter, string> = {
  all: 'All tasks',
  incomplete: 'Incomplete',
  completed: 'Completed',
  overdue: 'Carried over',
};

export default function CalendarScreen({ navigation }: any) {
  const colors = useColors();
  const { resolvedTheme } = useTheme();
  const insets = useSafeAreaInsets();
  const today = new Date();
  const todayString = localDateString(today);
  const [selectedDate, setSelectedDate] = useState(todayString);
  const [visibleMonth, setVisibleMonth] = useState({
    year: today.getFullYear(),
    month: today.getMonth() + 1,
  });
  const [dotDates, setDotDates] = useState<string[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [filter, setFilter] = useState<Filter>('all');
  const [showFilterMenu, setShowFilterMenu] = useState(false);
  const [activeTask, setActiveTask] = useState<Task | null>(null);
  const taskRequest = useRef(0);

  const loadDots = useCallback(async () => {
    try {
      setDotDates(await getCalendarDates(visibleMonth.year, visibleMonth.month));
    } catch (error) {
      console.log('Failed to load calendar dots:', error);
    }
  }, [visibleMonth]);

  const loadTasks = useCallback(async () => {
    const requestId = ++taskRequest.current;
    try {
      const result = await getTasksByDate(selectedDate, filter);
      if (requestId === taskRequest.current) setTasks(result);
    } catch (error) {
      console.log('Failed to load tasks for date:', error);
    }
  }, [selectedDate, filter]);

  const refresh = useCallback(() => {
    void loadDots();
    void loadTasks();
  }, [loadDots, loadTasks]);

  useFocusEffect(
    useCallback(() => {
      refresh();
    }, [refresh]),
  );

  const completeOptimistically = useTaskCompletion([setTasks], refresh);
  const markedDates = useMemo(() => {
    const marks: Record<string, any> = {};
    dotDates.forEach((date) => {
      marks[date] = { marked: true, dotColor: colors.primary };
    });
    marks[selectedDate] = {
      ...(marks[selectedDate] ?? {}),
      selected: true,
      selectedColor: colors.primary,
    };
    return marks;
  }, [dotDates, selectedDate, colors.primary]);

  const isToday = selectedDate === todayString;
  const incompleteTasks = tasks.filter((task) => task.status !== 'completed');
  const completedTasks = tasks.filter((task) => task.status === 'completed');
  const selectedLabel = new Date(`${selectedDate}T00:00:00`).toLocaleDateString(undefined, {
    weekday: 'long',
    day: 'numeric',
    month: 'short',
  });

  function goToToday() {
    const now = new Date();
    setSelectedDate(localDateString(now));
    setVisibleMonth({ year: now.getFullYear(), month: now.getMonth() + 1 });
  }

  const header = (
    <View>
      <View style={{ flexDirection: 'row', alignItems: 'center', paddingHorizontal: 20, paddingTop: insets.top + 12 }}>
        <TouchableOpacity
          onPress={() => navigation.goBack()}
          hitSlop={12}
          accessibilityRole="button"
          accessibilityLabel="Back"
          style={{ marginRight: 12 }}
        >
          <Ionicons name="arrow-back" size={24} color={colors.text} />
        </TouchableOpacity>
        <View style={{ flex: 1 }}>
          <Text style={{ color: colors.text, fontSize: 26, fontWeight: '800' }}>Calendar</Text>
          <Text style={{ color: colors.textMuted, fontSize: 13, marginTop: 2 }}>Plan your day, make progress.</Text>
        </View>
        <TouchableOpacity
          onPress={() => navigation.navigate('CreateTask', { prefilledDate: selectedDate })}
          accessibilityRole="button"
          accessibilityLabel="Add task"
          style={{ width: 44, height: 44, borderRadius: 14, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' }}
        >
          <Ionicons name="add" size={26} color="#fff" />
        </TouchableOpacity>
      </View>

      <View
        style={{
          marginHorizontal: 16,
          marginTop: 18,
          borderRadius: 20,
          overflow: 'hidden',
          borderWidth: 1,
          borderColor: colors.border,
          backgroundColor: colors.surface,
        }}
      >
        <Calendar
          key={resolvedTheme}
          current={selectedDate}
          markedDates={markedDates}
          onDayPress={(day: DateData) => setSelectedDate(day.dateString)}
          onMonthChange={(month: DateData) => setVisibleMonth({ year: month.year, month: month.month })}
          enableSwipeMonths
          theme={{
            calendarBackground: colors.surface,
            textSectionTitleColor: colors.textMuted,
            dayTextColor: colors.text,
            textDisabledColor: colors.border,
            todayTextColor: colors.primary,
            selectedDayBackgroundColor: colors.primary,
            selectedDayTextColor: '#FFFFFF',
            monthTextColor: colors.text,
            arrowColor: colors.primary,
            dotColor: colors.primary,
            selectedDotColor: '#FFFFFF',
            textMonthFontWeight: '700',
            textMonthFontSize: 17,
            textDayFontWeight: '500',
            textDayHeaderFontWeight: '600',
          }}
        />
      </View>

      <View style={{ flexDirection: 'row', alignItems: 'center', paddingHorizontal: 20, marginTop: 22, marginBottom: 6 }}>
        <View style={{ flex: 1 }}>
          <View style={{ flexDirection: 'row', alignItems: 'center' }}>
            <Text style={{ color: colors.text, fontSize: 17, fontWeight: '700' }}>{selectedLabel}</Text>
            {isToday ? (
              <View style={{ backgroundColor: colors.primarySoft, borderRadius: 999, paddingHorizontal: 10, paddingVertical: 3, marginLeft: 8 }}>
                <Text style={{ color: colors.primary, fontSize: 11, fontWeight: '700' }}>Today</Text>
              </View>
            ) : (
              <TouchableOpacity onPress={goToToday} style={{ marginLeft: 8 }} hitSlop={8}>
                <Text style={{ color: colors.primary, fontSize: 12, fontWeight: '700' }}>Jump to today</Text>
              </TouchableOpacity>
            )}
          </View>
        </View>
        <TouchableOpacity
          onPress={() => setShowFilterMenu(true)}
          style={{ flexDirection: 'row', alignItems: 'center', backgroundColor: colors.primarySoft, borderRadius: 999, paddingHorizontal: 12, paddingVertical: 6 }}
        >
          <Text style={{ color: colors.primary, fontSize: 12, fontWeight: '600' }}>
            {filter === 'all' ? `${tasks.length} ${tasks.length === 1 ? 'task' : 'tasks'}` : FILTER_LABELS[filter]}
          </Text>
          <Ionicons name="chevron-down" size={14} color={colors.primary} style={{ marginLeft: 4 }} />
        </TouchableOpacity>
      </View>
    </View>
  );

  return (
    <View style={{ flex: 1, backgroundColor: colors.background }}>
      <FlatList
        data={incompleteTasks}
        keyExtractor={(task) => task.id}
        ListHeaderComponent={header}
        contentContainerStyle={{ paddingBottom: 40 }}
        showsVerticalScrollIndicator={false}
        renderItem={({ item }) => (
          <View style={{ paddingHorizontal: 20 }}>
            <TaskRow
              task={item}
              onPress={() => navigation.navigate('TaskDetail', { taskId: item.id })}
              onToggleComplete={() => completeOptimistically(item)}
              onMore={() => setActiveTask(item)}
            />
          </View>
        )}
        ListEmptyComponent={
          completedTasks.length === 0 ? (
            <View style={{ alignItems: 'center', marginTop: 36, paddingHorizontal: 20 }}>
              <Ionicons name="leaf-outline" size={34} color={colors.textMuted} />
              <Text style={{ color: colors.text, fontWeight: '700', marginTop: 10 }}>Nothing planned yet</Text>
              <Text style={{ color: colors.textMuted, fontSize: 13, marginTop: 4 }}>A clear day is okay.</Text>
              <TouchableOpacity
                onPress={() => navigation.navigate('CreateTask', { prefilledDate: selectedDate })}
                style={{ marginTop: 16, backgroundColor: colors.primarySoft, borderRadius: 999, paddingHorizontal: 18, paddingVertical: 10 }}
              >
                <Text style={{ color: colors.primary, fontWeight: '700' }}>+ Add a task</Text>
              </TouchableOpacity>
            </View>
          ) : null
        }
        ListFooterComponent={
          completedTasks.length > 0 ? (
            <View style={{ marginTop: 18, paddingHorizontal: 20 }}>
              <Text style={{ color: colors.textMuted, fontWeight: '700', fontSize: 13, marginBottom: 2 }}>
                Completed ({completedTasks.length})
              </Text>
              {completedTasks.map((task) => (
                <TaskRow
                  key={task.id}
                  task={task}
                  onPress={() => navigation.navigate('TaskDetail', { taskId: task.id })}
                  onToggleComplete={() => completeOptimistically(task)}
                  onMore={() => setActiveTask(task)}
                />
              ))}
            </View>
          ) : null
        }
      />

      <Modal visible={showFilterMenu} transparent animationType="fade" onRequestClose={() => setShowFilterMenu(false)}>
        <Pressable style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.3)' }} onPress={() => setShowFilterMenu(false)}>
          <View
            style={{
              position: 'absolute',
              right: 16,
              top: insets.top + 330,
              width: 190,
              backgroundColor: colors.surface,
              borderRadius: 16,
              borderWidth: 1,
              borderColor: colors.border,
              overflow: 'hidden',
            }}
          >
            {FILTERS.map((value) => (
              <TouchableOpacity
                key={value}
                onPress={() => {
                  setFilter(value);
                  setShowFilterMenu(false);
                }}
                style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingVertical: 13 }}
              >
                <Text style={{ color: colors.text, fontWeight: value === filter ? '700' : '400' }}>{FILTER_LABELS[value]}</Text>
                {value === filter && <Ionicons name="checkmark" size={18} color={colors.primary} />}
              </TouchableOpacity>
            ))}
          </View>
        </Pressable>
      </Modal>

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
