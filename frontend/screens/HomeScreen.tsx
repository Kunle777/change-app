import { useCallback, useState } from 'react';
import { useFocusEffect } from '@react-navigation/native';
import { FlatList, RefreshControl, ScrollView, Text, TouchableOpacity, View } from 'react-native';
import ElvynMascot from '../components/ElvynMascot';
import TaskActionSheet from '../components/tasks/TaskActionSheet';
import RescheduleSheet from '../components/tasks/RescheduleSheet';
import TaskRow from '../components/tasks/TaskRow';
import { getMyProfile } from '../services/users';
import {
  getTodayCheckinStatus,
  submitEveningCheckin,
  submitMorningCheckin,
} from '../services/checkins';
import {
  cancelTask,
  completeTask,
  getTasksByDate,
  notNowTask,
  rescheduleTask,
} from '../services/tasks';
import type { Task } from '../types/task';

const QUICK_MOOD_MAP: Record<string, number> = { 'Not great': 2, Okay: 3, Good: 4 };

function toDateString(date: Date) {
  return date.toISOString().split('T')[0];
}

function getTimeOfDay(): 'morning' | 'evening' {
  return new Date().getHours() < 12 ? 'morning' : 'evening';
}

function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

export default function HomeScreen({ navigation }: any) {
  const [firstName, setFirstName] = useState('');
  const [tasks, setTasks] = useState<Task[]>([]);
  const [checkInStatus, setCheckInStatus] = useState<{
    checkins_enabled: boolean;
    morning_done: boolean;
    evening_done: boolean;
  } | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTask, setActiveTask] = useState<Task | null>(null);
  const [sheetVisible, setSheetVisible] = useState(false);
  const [rescheduleVisible, setRescheduleVisible] = useState(false);

  const timeOfDay = getTimeOfDay();
  const alreadyCheckedIn =
    timeOfDay === 'morning' ? checkInStatus?.morning_done : checkInStatus?.evening_done;

  const loadAll = useCallback(async () => {
    try {
      const [profile, todayTasks, status] = await Promise.all([
        getMyProfile(),
        getTasksByDate(toDateString(new Date()), 'all'),
        getTodayCheckinStatus(),
      ]);
      setFirstName(profile.first_name ?? '');
      setTasks(todayTasks);
      setCheckInStatus(status);
    } catch (error) {
      console.log('Home load failed:', error);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      loadAll();
    }, [loadAll]),
  );

  async function handleRefresh() {
    setRefreshing(true);
    try {
      await loadAll();
    } finally {
      setRefreshing(false);
    }
  }

  async function handleQuickMood(label: string) {
    const mood = QUICK_MOOD_MAP[label];
    try {
      if (timeOfDay === 'morning') await submitMorningCheckin(mood, '');
      else await submitEveningCheckin(mood, '', null);
      await loadAll();
    } catch (error) {
      console.log('Quick check-in failed:', error);
    }
  }

  const completedCount = tasks.filter((task) => task.status === 'completed').length;
  const remaining = tasks.length - completedCount;

  return (
    <View style={{ flex: 1, backgroundColor: '#F8FAFC' }}>
      <View style={{ backgroundColor: '#1A1636', padding: 20, paddingTop: 50 }}>
        <Text style={{ color: '#fff', fontWeight: '700', fontSize: 16, letterSpacing: 2 }}>
          ELVYN
        </Text>
        <Text style={{ color: '#fff', fontSize: 22, fontWeight: '700', marginTop: 20 }}>
          {getGreeting()},
        </Text>
        <Text style={{ color: '#A78BFA', fontSize: 22, fontWeight: '700' }}>
          {firstName || 'there'}
        </Text>
        <View style={{ marginTop: 16 }}>
          <ElvynMascot variant="supportive" size={64} />
        </View>
      </View>

      <ScrollView
        style={{ flex: 1 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />}
      >
        <View
          style={{
            backgroundColor: '#fff',
            margin: 16,
            marginTop: -24,
            borderRadius: 16,
            padding: 16,
            flexDirection: 'row',
            alignItems: 'center',
            justifyContent: 'space-between',
            elevation: 2,
          }}
        >
          <View>
            <Text style={{ fontWeight: '700', fontSize: 15 }}>Today's Progress</Text>
            <Text style={{ color: '#888', fontSize: 12, marginTop: 2 }}>
              {completedCount} of {tasks.length} tasks completed
            </Text>
          </View>
          <Text style={{ color: '#4F46E5', fontWeight: '700' }}>
            {tasks.length > 0 ? `${remaining} left` : '—'}
          </Text>
        </View>

        <TouchableOpacity
          onPress={() => navigation.navigate('BrainDump')}
          style={{ backgroundColor: '#fff', marginHorizontal: 16, marginBottom: 16, borderRadius: 16, padding: 16 }}
        >
          <Text style={{ fontWeight: '700', fontSize: 15 }}>What's on your mind?</Text>
          <Text style={{ color: '#888', fontSize: 12, marginTop: 4 }}>
            Capture ideas, tasks, or anything on your mind. Elvyn will help you turn it into action.
          </Text>
        </TouchableOpacity>

        <View style={{ backgroundColor: '#FFF7ED', marginHorizontal: 16, marginBottom: 16, borderRadius: 16, padding: 16 }}>
          <Text style={{ fontWeight: '700', fontSize: 15 }}>
            How are you {timeOfDay === 'morning' ? 'this morning' : 'this evening'}?
          </Text>
          {alreadyCheckedIn ? (
            <Text style={{ color: '#10B981', marginTop: 8, fontWeight: '600' }}>✓ Checked in</Text>
          ) : (
            <View style={{ flexDirection: 'row', gap: 8, marginTop: 12 }}>
              {['Good', 'Okay', 'Not great'].map((label) => (
                <TouchableOpacity
                  key={label}
                  onPress={() => handleQuickMood(label)}
                  style={{ flex: 1, paddingVertical: 10, borderRadius: 10, borderWidth: 1, borderColor: '#E5C99B', alignItems: 'center' }}
                >
                  <Text style={{ fontSize: 12 }}>{label}</Text>
                </TouchableOpacity>
              ))}
            </View>
          )}
          <TouchableOpacity onPress={() => navigation.navigate('CheckIn', { type: timeOfDay })} style={{ marginTop: 12 }}>
            <Text style={{ color: '#4F46E5', fontWeight: '600' }}>Check in →</Text>
          </TouchableOpacity>
        </View>

        <TouchableOpacity
          onPress={() => navigation.navigate('Calendar')}
          style={{ backgroundColor: '#fff', marginHorizontal: 16, marginBottom: 16, borderRadius: 16, padding: 16, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}
        >
          <Text style={{ fontWeight: '600' }}>
            Today, {new Date().toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
          </Text>
          <Text style={{ color: '#4F46E5' }}>View calendar →</Text>
        </TouchableOpacity>

        <View style={{ backgroundColor: '#fff', marginHorizontal: 16, borderRadius: 16, padding: 16, marginBottom: 24 }}>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 }}>
            <Text style={{ fontWeight: '700', fontSize: 15 }}>
              Today's Tasks <Text style={{ fontSize: 12, color: '#888' }}>({remaining} left)</Text>
            </Text>
            <TouchableOpacity onPress={() => navigation.navigate('Calendar')}>
              <Text style={{ color: '#4F46E5', fontSize: 12 }}>See all →</Text>
            </TouchableOpacity>
          </View>
          <FlatList
            data={tasks}
            keyExtractor={(task) => task.id}
            scrollEnabled={false}
            ListEmptyComponent={<Text style={{ color: '#888', paddingVertical: 12 }}>No tasks today.</Text>}
            renderItem={({ item }) => (
              <TaskRow
                task={item}
                onPress={() => navigation.navigate('TaskDetail', { taskId: item.id })}
                onToggleComplete={() => completeTask(item.id).then(loadAll)}
                onMore={() => {
                  setActiveTask(item);
                  setSheetVisible(true);
                }}
              />
            )}
          />
          <TouchableOpacity
            onPress={() => navigation.navigate('CreateTask')}
            style={{ backgroundColor: '#4F46E5', borderRadius: 10, padding: 14, alignItems: 'center', marginTop: 12 }}
          >
            <Text style={{ color: '#fff', fontWeight: '600' }}>+ Create task</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>

      <TaskActionSheet
        visible={sheetVisible}
        onClose={() => setSheetVisible(false)}
        onMarkDone={() => activeTask && completeTask(activeTask.id).then(loadAll)}
        onNotNow={() => activeTask && notNowTask(activeTask.id, 'later_today').then(loadAll)}
        onReschedule={() => setRescheduleVisible(true)}
        onEdit={() => activeTask && navigation.navigate('CreateTask', { taskId: activeTask.id })}
        onCancel={() => activeTask && cancelTask(activeTask.id).then(loadAll)}
      />
      <RescheduleSheet
        visible={rescheduleVisible}
        task={activeTask}
        onClose={() => setRescheduleVisible(false)}
        onSave={async (dueDate, reminderTime) => {
          if (activeTask) {
            await rescheduleTask(activeTask.id, dueDate, reminderTime);
            await loadAll();
          }
        }}
      />
    </View>
  );
}
