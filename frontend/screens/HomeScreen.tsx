import { useCallback, useState } from 'react';
import { useFocusEffect } from '@react-navigation/native';
import { RefreshControl, ScrollView, Text, TouchableOpacity, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import ElvynMascot from '../components/ElvynMascot';
import ProgressRing from '../components/home/progress_ring';
import TaskActionsHost from '../components/tasks/TaskActionsHost';
import { useTaskCompletion } from '../hooks/useTaskCompletion';
import { localDateString } from '../utils/localDate';
import TaskRow from '../components/tasks/TaskRow';
import { getMyProfile } from '../services/users';
import {
  getTodayCheckinStatus,
  submitEveningCheckin,
  submitMorningCheckin,
} from '../services/checkins';
import { getTasksByDate, getUndatedTasks } from '../services/tasks';
import { getEveningPrompt, getMorningPrompt } from './ElvynContextPrompt';
import { useColors } from '../theme/colors';
import type { Task } from '../types/task';

const QUICK_MOODS = [
  { label: 'Good', emoji: '🙂', value: 4 },
  { label: 'Okay', emoji: '😐', value: 3 },
  { label: 'Not great', emoji: '😕', value: 2 },
];

function getTimeOfDay(): 'morning' | 'evening' {
  return new Date().getHours() < 12 ? 'morning' : 'evening';
}

function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

type CheckInStatus = { checkins_enabled: boolean; morning_done: boolean; evening_done: boolean };

export default function HomeScreen({ navigation }: any) {
  const colors = useColors();
  const insets = useSafeAreaInsets();

  const [firstName, setFirstName] = useState('');
  const [tasks, setTasks] = useState<Task[]>([]);
  const [undatedTasks, setUndatedTasks] = useState<Task[]>([]);
  const [undatedTasksError, setUndatedTasksError] = useState(false);
  const [checkInStatus, setCheckInStatus] = useState<CheckInStatus | null>(null);
  const [checkingIn, setCheckingIn] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTask, setActiveTask] = useState<Task | null>(null);

  const timeOfDay = getTimeOfDay();
  const heroPrompt = timeOfDay === 'morning' ? getMorningPrompt() : getEveningPrompt();
  const alreadyCheckedIn =
    timeOfDay === 'morning' ? checkInStatus?.morning_done : checkInStatus?.evening_done;

  const loadAll = useCallback(async () => {
    try {
      const [profile, todayTasks, status] = await Promise.all([
        getMyProfile(),
        getTasksByDate(localDateString(new Date()), 'all'),
        getTodayCheckinStatus(),
      ]);
      setFirstName(profile.first_name ?? '');
      setTasks(todayTasks.filter((t: Task) => t.status !== 'cancelled'));
      setCheckInStatus(status);
      setUndatedTasksError(false);
      void getUndatedTasks()
        .then(setUndatedTasks)
        .catch((error) => {
          console.log('Undated tasks load failed:', error);
          setUndatedTasksError(true);
        });
    } catch (error) {
      console.log('Home load failed:', error);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      loadAll();
    }, [loadAll]),
  );

  const reload = useCallback(() => {
    void loadAll();
  }, [loadAll]);
  const completeOptimistically = useTaskCompletion([setTasks, setUndatedTasks], reload);

  async function handleRefresh() {
    setRefreshing(true);
    try {
      await loadAll();
    } finally {
      setRefreshing(false);
    }
  }

  async function handleQuickMood(mood: number) {
    if (checkingIn) return;
    setCheckingIn(true);
    try {
      if (timeOfDay === 'morning') await submitMorningCheckin(mood, '');
      else await submitEveningCheckin(mood, '', null);
      await loadAll();
    } catch (error) {
      console.log('Quick check-in failed:', error);
    } finally {
      setCheckingIn(false);
    }
  }

  const total = tasks.length;
  const completedCount = tasks.filter((t) => t.status === 'completed').length;
  const percent = total > 0 ? Math.round((completedCount / total) * 100) : 0;

  const card = {
    backgroundColor: colors.surface,
    marginHorizontal: 16,
    marginBottom: 16,
    borderRadius: 16,
    padding: 16,
  } as const;

  const taskHandlers = (item: Task) => ({
    onPress: () => navigation.navigate('TaskDetail', { taskId: item.id }),
    onToggleComplete: () => completeOptimistically(item),
    onMore: () => setActiveTask(item),
  });

  return (
    <View style={{ flex: 1, backgroundColor: colors.background }}>
      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={{ paddingBottom: 24 }}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} tintColor={colors.primary} />
        }
      >
        {/* Hero */}
        <View
          style={{
            backgroundColor: colors.heroBg,
            paddingTop: insets.top + 12,
            paddingHorizontal: 20,
            paddingBottom: 56,
            borderBottomLeftRadius: 28,
            borderBottomRightRadius: 28,
          }}
        >
          {/* Step 3: streak pill goes on the right of this row */}
          <Text style={{ color: '#fff', fontWeight: '700', fontSize: 16, letterSpacing: 3 }}>ELVYN</Text>

          <View style={{ flexDirection: 'row', alignItems: 'center', marginTop: 20 }}>
            <View style={{ flex: 1, paddingRight: 8 }}>
              <Text style={{ color: '#E5E7EB', fontSize: 20 }}>{getGreeting()},</Text>
              <Text style={{ color: '#fff', fontSize: 26, fontWeight: '800' }}>{firstName || 'there'}</Text>
              <Text style={{ color: '#C4B5FD', fontSize: 14, lineHeight: 20, marginTop: 10 }}>{heroPrompt}</Text>
            </View>
           <ElvynMascot variant="supportive" size={96} />

          </View>
        </View>

        {/* Progress */}
        <View
          style={{
            ...card,
            marginTop: -32,
            flexDirection: 'row',
            alignItems: 'center',
            elevation: 3,
            shadowColor: '#000',
            shadowOpacity: 0.08,
            shadowRadius: 8,
            shadowOffset: { width: 0, height: 2 },
          }}
        >
          {total > 0 ? (
            <>
              <ProgressRing
                percent={percent}
                color={colors.primary}
                track={colors.primarySoft}
                textColor={colors.text}
              />
              <View style={{ marginLeft: 16, flex: 1 }}>
                <Text style={{ color: colors.text, fontWeight: '700', fontSize: 16 }}>Today's Progress</Text>
                <Text style={{ color: colors.textMuted, marginTop: 2 }}>
                  {completedCount} of {total} tasks done
                </Text>
              </View>
            </>
          ) : (
            <View>
              <Text style={{ color: colors.text, fontWeight: '700', fontSize: 16 }}>Today's Progress</Text>
              <Text style={{ color: colors.textMuted, marginTop: 2 }}>No tasks today. A clear day is okay.</Text>
            </View>
          )}
        </View>

        {/* Brain Dump */}
        <TouchableOpacity onPress={() => navigation.navigate('BrainDump')} style={card}>
          <Text style={{ color: colors.text, fontWeight: '700', fontSize: 15 }}>What's on your mind?</Text>
          <Text style={{ color: colors.textMuted, fontSize: 13, marginTop: 4, lineHeight: 18 }}>
            Capture ideas, tasks, or anything on your mind. Elvyn will help you turn it into action.
          </Text>
        </TouchableOpacity>

        {/* Check-in: hidden entirely when check-ins are turned off */}
        {checkInStatus?.checkins_enabled && (
          <View style={{ ...card, backgroundColor: colors.warmSurface }}>
            {alreadyCheckedIn ? (
              <Text style={{ color: colors.success, fontWeight: '700' }}>✓ Checked in</Text>
            ) : (
              <>
                <Text style={{ color: colors.text, fontWeight: '700', fontSize: 15 }}>
                  How are you {timeOfDay === 'morning' ? 'this morning' : 'this evening'}?
                </Text>
                <View style={{ flexDirection: 'row', gap: 8, marginTop: 12 }}>
                  {QUICK_MOODS.map((m) => (
                    <TouchableOpacity
                      key={m.label}
                      disabled={checkingIn}
                      onPress={() => handleQuickMood(m.value)}
                      style={{
                        flex: 1,
                        paddingVertical: 10,
                        borderRadius: 12,
                        borderWidth: 1,
                        borderColor: colors.warmBorder,
                        backgroundColor: colors.surface,
                        alignItems: 'center',
                        opacity: checkingIn ? 0.6 : 1,
                      }}
                    >
                      <Text style={{ fontSize: 18 }}>{m.emoji}</Text>
                      <Text style={{ fontSize: 12, color: colors.text, marginTop: 2 }}>{m.label}</Text>
                    </TouchableOpacity>
                  ))}
                </View>
                <TouchableOpacity
                  onPress={() => navigation.navigate('CheckIn', { type: timeOfDay })}
                  style={{ marginTop: 12 }}
                >
                  <Text style={{ color: colors.primary, fontWeight: '600' }}>Check in →</Text>
                </TouchableOpacity>
              </>
            )}
          </View>
        )}

        {/* Calendar: the single entry point, sits directly above Today's Tasks */}
        <TouchableOpacity
          onPress={() => navigation.navigate('Calendar')}
          style={{ ...card, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}
        >
          <Text style={{ color: colors.text, fontWeight: '600' }}>
            Today, {new Date().toLocaleDateString(undefined, { day: 'numeric', month: 'short' })}
          </Text>
          <Text style={{ color: colors.primary }}>View calendar →</Text>
        </TouchableOpacity>

        {/* Today's Tasks */}
        <View style={card}>
          <Text style={{ color: colors.text, fontWeight: '700', fontSize: 15, marginBottom: 4 }}>
            Today's Tasks
          </Text>
          {tasks.length === 0 ? (
            <Text style={{ color: colors.textMuted, paddingVertical: 12 }}>No tasks today.</Text>
          ) : (
            tasks.map((item) => <TaskRow key={item.id} task={item} {...taskHandlers(item)} />)
          )}
          <TouchableOpacity
            onPress={() => navigation.navigate('CreateTask')}
            style={{
              backgroundColor: colors.primary,
              borderRadius: 12,
              padding: 14,
              alignItems: 'center',
              marginTop: 12,
            }}
          >
            <Text style={{ color: '#fff', fontWeight: '600' }}>+ Create task</Text>
          </TouchableOpacity>
        </View>

        {/* To-do (no date): refined in step 4 */}
        {(undatedTasks.length > 0 || undatedTasksError) && (
          <View style={card}>
            <Text style={{ color: colors.text, fontWeight: '700', fontSize: 15, marginBottom: 4 }}>
              To-do <Text style={{ fontSize: 12, color: colors.textMuted }}>(no date)</Text>
            </Text>
            {undatedTasksError && (
              <Text style={{ color: colors.textMuted, paddingVertical: 8 }}>
                Couldn't load your to-do list. Pull down to try again.
              </Text>
            )}
            {undatedTasks.map((item) => (
              <TaskRow key={item.id} task={item} {...taskHandlers(item)} />
            ))}
          </View>
        )}
      </ScrollView>

      <TaskActionsHost
        task={activeTask}
        onClose={() => setActiveTask(null)}
        onChanged={reload}
        onMarkDone={completeOptimistically}
        navigation={navigation}
      />
    </View>
  );
}