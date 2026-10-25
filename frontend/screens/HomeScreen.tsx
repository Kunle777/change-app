import { useCallback, useState } from 'react';
import { useFocusEffect } from '@react-navigation/native';
import { RefreshControl, ScrollView, Text, TouchableOpacity, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import ElvynMascot from '../components/ElvynMascot';
import ProgressRing from '../components/home/progress_ring';
import TaskActionsHost from '../components/tasks/TaskActionsHost';
import TaskRow from '../components/tasks/TaskRow';
import { getMyProfile } from '../services/users';
import { getTodayCheckinStatus, submitEveningCheckin, submitMorningCheckin } from '../services/checkins';
import { completeTask, getTasksByDate, getUndatedTasks } from '../services/tasks';
import { getEveningPrompt, getMorningPrompt } from './ElvynContextPrompt';
import { useColors } from '../theme/colors';
import type { Task } from '../types/task';

const MOODS = [
  { label: 'Good', emoji: '🙂', value: 4, tint: '#10B981' },
  { label: 'Okay', emoji: '😐', value: 3, tint: '#F59E0B' },
  { label: 'Not great', emoji: '🙁', value: 2, tint: '#EF4444' },
];

function localDateString(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
const getTimeOfDay = (): 'morning' | 'evening' => (new Date().getHours() < 12 ? 'morning' : 'evening');
function getGreeting() {
  const h = new Date().getHours();
  return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
}

type CheckInStatus = { checkins_enabled: boolean; morning_done: boolean; evening_done: boolean };

function IconTile({ name, color, bg }: { name: keyof typeof Ionicons.glyphMap; color: string; bg: string }) {
  return (
    <View style={{ width: 48, height: 48, borderRadius: 14, backgroundColor: bg, alignItems: 'center', justifyContent: 'center' }}>
      <Ionicons name={name} size={24} color={color} />
    </View>
  );
}

function Pill({ label, bg, color }: { label: string; bg: string; color: string }) {
  return (
    <View style={{ backgroundColor: bg, borderRadius: 999, paddingHorizontal: 12, paddingVertical: 6 }}>
      <Text style={{ color, fontSize: 12, fontWeight: '600' }}>{label}</Text>
    </View>
  );
}

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
  const [sheetVisible, setSheetVisible] = useState(false);

  const timeOfDay = getTimeOfDay();
  const heroPrompt = timeOfDay === 'morning' ? getMorningPrompt() : getEveningPrompt();
  const alreadyCheckedIn = timeOfDay === 'morning' ? checkInStatus?.morning_done : checkInStatus?.evening_done;

  const loadAll = useCallback(async () => {
    try {
      const [profile, todayTasks, status] = await Promise.all([
        getMyProfile(),
        getTasksByDate(localDateString(new Date()), 'all'),
        getTodayCheckinStatus(),
      ]);
      setFirstName(profile.first_name ?? '');
      setTasks((todayTasks ?? []).filter((t: Task) => t.status !== 'cancelled'));
      setCheckInStatus(status);
      setUndatedTasksError(false);
      void getUndatedTasks().then(setUndatedTasks).catch(() => setUndatedTasksError(true));
    } catch (error) {
      console.log('Home load failed:', error);
    }
  }, []);

  useFocusEffect(useCallback(() => { loadAll(); }, [loadAll]));

  async function handleRefresh() {
    setRefreshing(true);
    try { await loadAll(); } finally { setRefreshing(false); }
  }

  async function handleQuickMood(mood: number) {
    if (checkingIn) return;
    setCheckingIn(true);
    try {
      if (timeOfDay === 'morning') await submitMorningCheckin(mood, '');
      else await submitEveningCheckin(mood, '', null);
      await loadAll();
    } catch (e) {
      console.log('Quick check-in failed:', e);
    } finally {
      setCheckingIn(false);
    }
  }

  const total = tasks.length;
  const done = tasks.filter((t) => t.status === 'completed').length;
  const remaining = total - done;
  const percent = total > 0 ? Math.round((done / total) * 100) : 0;

  const card = {
    backgroundColor: colors.surface,
    marginHorizontal: 16,
    marginBottom: 14,
    borderRadius: 20,
    padding: 16,
    borderWidth: 1,
    borderColor: colors.border,
  } as const;

  const handlers = (item: Task) => ({
    onPress: () => navigation.navigate('TaskDetail', { taskId: item.id }),
    onToggleComplete: () => completeTask(item.id).then(loadAll),
    onMore: () => { setActiveTask(item); setSheetVisible(true); },
  });

  const title = { color: colors.text, fontWeight: '700', fontSize: 17 } as const;
  const sub = { color: colors.textMuted, fontSize: 13, marginTop: 2 } as const;

  return (
    <View style={{ flex: 1, backgroundColor: colors.background }}>
      <ScrollView
        contentContainerStyle={{ paddingBottom: 24 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={handleRefresh} tintColor={colors.primary} />}
      >
        {/* Hero */}
        <View style={{ backgroundColor: colors.heroBg, paddingTop: insets.top + 12, paddingHorizontal: 20, paddingBottom: 56, borderBottomLeftRadius: 32, borderBottomRightRadius: 32 }}>
          <Text style={{ color: '#fff', fontWeight: '800', fontSize: 17, letterSpacing: 4 }}>ELVYN</Text>

          <Text style={{ color: '#C7C4E6', fontSize: 22, fontWeight: '400', marginTop: 26 }}>{getGreeting()},</Text>
          <Text style={{ color: '#fff', fontSize: 34, fontWeight: '800', marginTop: 2 }} numberOfLines={1}>
            {firstName || 'there'}
          </Text>

          <View style={{ flexDirection: 'row', alignItems: 'flex-end', marginTop: 16 }}>
            <View
              style={{
                flex: 1,
                marginRight: 6,
                backgroundColor: 'rgba(255,255,255,0.07)',
                borderWidth: 1,
                borderColor: 'rgba(255,255,255,0.14)',
                borderRadius: 18,
                padding: 14,
              }}
            >
              <Text style={{ color: '#A78BFA', fontSize: 30, fontWeight: '800', lineHeight: 30 }}>“</Text>
              <Text style={{ color: '#EDEBFF', fontSize: 14, lineHeight: 21 }}>{heroPrompt}</Text>
              <Text style={{ color: '#9C98C9', fontSize: 12, marginTop: 10 }}>— ELVYN</Text>
            </View>
            <View style={{ marginBottom: -4 }}>
              <ElvynMascot variant="supportive" size={110} />
            </View>
          </View>
        </View>

        {/* Progress */}
        <View
          style={{
            ...card,
            marginTop: -34,
            flexDirection: 'row',
            alignItems: 'center',
            elevation: 4,
            shadowColor: '#000',
            shadowOpacity: 0.08,
            shadowRadius: 10,
            shadowOffset: { width: 0, height: 3 },
          }}
        >
          {total > 0 ? (
            <>
              <ProgressRing percent={percent} color={colors.primary} track={colors.primarySoft} textColor={colors.text} />
              <View style={{ flex: 1, marginLeft: 16 }}>
                <Text style={title}>Today's Progress</Text>
                <Text style={sub}>{done} of {total} tasks completed</Text>
              </View>
              {remaining > 0 && <Pill label={`${remaining} remaining`} bg={colors.primarySoft} color={colors.primary} />}
            </>
          ) : (
            <View>
              <Text style={title}>Today's Progress</Text>
              <Text style={sub}>No tasks today. A clear day is okay.</Text>
            </View>
          )}
        </View>

        {/* Brain Dump */}
        <TouchableOpacity
          onPress={() => navigation.navigate('BrainDump')}
          style={{ ...card, backgroundColor: colors.lavenderSurface, flexDirection: 'row', alignItems: 'center' }}
        >
          <IconTile name="bulb-outline" color={colors.primary} bg={colors.primarySoft} />
          <View style={{ flex: 1, marginLeft: 14, marginRight: 8 }}>
            <Text style={title}>Brain Dump</Text>
            <Text style={{ color: colors.text, fontSize: 14, marginTop: 2 }}>What's on your mind?</Text>
            <Text style={{ ...sub, lineHeight: 18 }}>Capture ideas, tasks, or anything. Elvyn will help you turn it into action.</Text>
          </View>
          <View style={{ backgroundColor: colors.primarySoft, borderRadius: 999, padding: 10 }}>
            <Ionicons name="mic-outline" size={20} color={colors.primary} />
          </View>
        </TouchableOpacity>

        {/* Check-in */}
        {checkInStatus?.checkins_enabled && (
          <View style={{ ...card, backgroundColor: colors.warmSurface, borderColor: colors.warmBorder }}>
            <View style={{ flexDirection: 'row', alignItems: 'center' }}>
              <IconTile name="happy-outline" color="#F59E0B" bg={colors.surface} />
              <View style={{ marginLeft: 14, flex: 1 }}>
                <Text style={title}>Check-in</Text>
                <Text style={sub}>
                  {alreadyCheckedIn
                    ? 'You checked in today. Nice.'
                    : `How are you feeling this ${timeOfDay === 'morning' ? 'morning' : 'evening'}?`}
                </Text>
              </View>
              {alreadyCheckedIn && <Ionicons name="checkmark-circle" size={26} color={colors.success} />}
            </View>

            {!alreadyCheckedIn && (
              <>
                <View style={{ flexDirection: 'row', gap: 8, marginTop: 14 }}>
                  {MOODS.map((m) => (
                    <TouchableOpacity
                      key={m.label}
                      disabled={checkingIn}
                      onPress={() => handleQuickMood(m.value)}
                      style={{
                        flex: 1,
                        flexDirection: 'row',
                        alignItems: 'center',
                        justifyContent: 'center',
                        paddingVertical: 9,
                        borderRadius: 14,
                        backgroundColor: colors.surface,
                        borderWidth: 1,
                        borderColor: colors.warmBorder,
                        opacity: checkingIn ? 0.6 : 1,
                      }}
                    >
                      <View style={{ width: 24, height: 24, borderRadius: 12, backgroundColor: `${m.tint}22`, alignItems: 'center', justifyContent: 'center', marginRight: 6 }}>
                        <Text style={{ fontSize: 14 }}>{m.emoji}</Text>
                      </View>
                      <Text style={{ color: colors.text, fontSize: 12, fontWeight: '500' }}>{m.label}</Text>
                    </TouchableOpacity>
                  ))}
                </View>
                <TouchableOpacity onPress={() => navigation.navigate('CheckIn', { type: timeOfDay })} style={{ marginTop: 12 }}>
                  <Text style={{ color: colors.primary, fontWeight: '600' }}>Add more detail →</Text>
                </TouchableOpacity>
              </>
            )}
          </View>
        )}

        {/* Calendar (single entry point) */}
        <TouchableOpacity
          onPress={() => navigation.navigate('Calendar')}
          style={{ ...card, flexDirection: 'row', alignItems: 'center' }}
        >
          <IconTile name="calendar-outline" color={colors.primary} bg={colors.primarySoft} />
          <View style={{ flex: 1, marginLeft: 14 }}>
            <Text style={title}>Calendar</Text>
            <Text style={sub}>Today • {new Date().toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</Text>
          </View>
          <Text style={{ color: colors.primary, fontWeight: '600' }}>View calendar →</Text>
        </TouchableOpacity>

        {/* Today's Tasks */}
        <View style={card}>
          <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 6 }}>
            <IconTile name="list-outline" color={colors.primary} bg={colors.primarySoft} />
            <Text style={{ ...title, flex: 1, marginLeft: 14 }}>Today's Tasks</Text>
            {remaining > 0 && <Pill label={`${remaining} left`} bg={colors.primarySoft} color={colors.primary} />}
          </View>

          {tasks.length === 0 ? (
            <Text style={{ color: colors.textMuted, paddingVertical: 14 }}>No tasks today.</Text>
          ) : (
            tasks.map((item) => <TaskRow key={item.id} task={item} {...handlers(item)} />)
          )}

          <TouchableOpacity
            onPress={() => navigation.navigate('CreateTask')}
            style={{ backgroundColor: colors.primary, borderRadius: 14, padding: 15, alignItems: 'center', marginTop: 14 }}
          >
            <Text style={{ color: '#fff', fontWeight: '700' }}>+ Create task</Text>
          </TouchableOpacity>
        </View>

        {/* To-do (no date) */}
        {(undatedTasks.length > 0 || undatedTasksError) && (
          <View style={card}>
            <Text style={{ ...title, marginBottom: 4 }}>
              To-do <Text style={{ fontSize: 12, color: colors.textMuted, fontWeight: '400' }}>(no date)</Text>
            </Text>
            {undatedTasksError && (
              <Text style={{ color: colors.textMuted, paddingVertical: 8 }}>Couldn't load your to-do list. Pull down to try again.</Text>
            )}
            {undatedTasks.map((item) => <TaskRow key={item.id} task={item} {...handlers(item)} />)}
          </View>
        )}
      </ScrollView>

      <TaskActionsHost
        task={activeTask}
        visible={sheetVisible}
        onClose={() => setSheetVisible(false)}
        onChanged={loadAll}
        navigation={navigation}
      />
    </View>
  );
}