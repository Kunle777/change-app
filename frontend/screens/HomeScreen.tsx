import { useCallback, useState } from 'react';
import { useFocusEffect } from '@react-navigation/native';
import { Image, RefreshControl, ScrollView, TouchableOpacity, useWindowDimensions, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import ElvynMascot from '../components/ElvynMascot';
import AppText from '../components/ui/AppText';
import ProgressRing from '../components/home/progress_ring';
import TaskActionsHost from '../components/tasks/TaskActionsHost';
import TaskRow from '../components/tasks/TaskRow';
import { getMyProfile } from '../services/users';
import { getTodayCheckinStatus, submitEveningCheckin, submitMorningCheckin } from '../services/checkins';
import { getTasksByDate, getUndatedTasks } from '../services/tasks';
import { useTaskCompletion } from '../hooks/useTaskCompletion';
import { localDateString } from '../utils/localDate';
import { getEveningPrompt, getMorningPrompt } from './ElvynContextPrompt';
import { useColors } from '../theme/colors';
import type { Task } from '../types/task';

const MOODS = [
  { label: 'Good', emoji: '🙂', value: 4 },
  { label: 'Okay', emoji: '😐', value: 3 },
  { label: 'Not great', emoji: '🙁', value: 2 },
];

const getTimeOfDay = (): 'morning' | 'evening' => (new Date().getHours() < 12 ? 'morning' : 'evening');

function getGreeting() {
  const h = new Date().getHours();
  return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
}

type CheckInStatus = { checkins_enabled: boolean; morning_done: boolean; evening_done: boolean };

function IconTile({
  name,
  color,
  bg,
  size,
}: {
  name: keyof typeof Ionicons.glyphMap;
  color: string;
  bg: string;
  size: number;
}) {
  return (
    <View style={{ width: size, height: size, borderRadius: 14, backgroundColor: bg, alignItems: 'center', justifyContent: 'center' }}>
      <Ionicons name={name} size={size * 0.5} color={color} />
    </View>
  );
}

function Pill({ label, bg, color, scale }: { label: string; bg: string; color: string; scale: number }) {
  return (
    <View style={{ backgroundColor: bg, borderRadius: 999, paddingHorizontal: 10 * scale, paddingVertical: 5 * scale }}>
      <AppText variant="body" style={{ color, fontWeight: '600' }}>{label}</AppText>
    </View>
  );
}

export default function HomeScreen({ navigation }: any) {
  const colors = useColors();
  const insets = useSafeAreaInsets();
  const { width, fontScale } = useWindowDimensions();
  const scale = Math.min(1.1, Math.max(0.9, width / 390));
  const gutter = 20 * scale;
  const tileSize = 44 * scale;
  const mascotSize = Math.min(120, Math.max(84, width * 0.28));
  const stackedHero = width < 360 || fontScale > 1.3;
  const heroMascotSize = stackedHero ? Math.min(mascotSize, Math.max(84, width * 0.24)) : mascotSize;

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

  const reload = useCallback(() => {
    void loadAll();
  }, [loadAll]);
  const completeOptimistically = useTaskCompletion([setTasks, setUndatedTasks], reload);

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
    marginHorizontal: gutter,
    marginBottom: 12 * scale,
    borderRadius: 20 * scale,
    padding: 16 * scale,
    borderWidth: 1,
    borderColor: colors.border,
  } as const;

  const handlers = (item: Task) => ({
    onPress: () => navigation.navigate('TaskDetail', { taskId: item.id }),
    onToggleComplete: () => completeOptimistically(item),
    onMore: () => setActiveTask(item),
  });

  return (
    <View style={{ flex: 1, backgroundColor: colors.background }}>
      <ScrollView
        contentContainerStyle={{ paddingBottom: 24 * scale }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={handleRefresh} tintColor={colors.primary} />}
      >
        {/* Hero */}
        <View
          style={{
            width: '100%',
            overflow: 'hidden',
            backgroundColor: colors.heroBg,
            paddingTop: insets.top + 12 * scale,
            paddingHorizontal: gutter,
            paddingBottom: 42 * scale,
            borderBottomLeftRadius: 28,
            borderBottomRightRadius: 28,
          }}
        >
          <View style={{ flexDirection: 'row', alignItems: 'center', marginTop: 10 * scale }}>
            <Image
              source={require('../assets/branding/04_mark_only_monochrome_dark.png')}
              resizeMode="contain"
              accessibilityLabel="Elvyn"
              style={{ width: 48 * scale, height: 48 * scale, marginRight: 12 * scale }}
            />
            <View style={{ flex: 1, minWidth: 0 }}>
              {firstName.trim() ? (
                <>
                  <AppText variant="greeting" style={{ color: '#C7C4E6' }}>
                    {getGreeting()},
                  </AppText>
                  <AppText
                    variant="display"
                    accessibilityRole="header"
                    numberOfLines={1}
                    ellipsizeMode="tail"
                    style={{ color: '#fff', marginTop: 1 * scale }}
                  >
                    {firstName.trim()}
                  </AppText>
                </>
              ) : (
                <AppText variant="display" accessibilityRole="header" style={{ color: '#fff' }}>
                  {getGreeting()}
                </AppText>
              )}
            </View>
          </View>

          <View
            style={{
              flexDirection: stackedHero ? 'column' : 'row',
              alignItems: stackedHero ? 'stretch' : 'flex-end',
              marginTop: 18 * scale,
            }}
          >
            <View
              style={{
                flex: 1,
                minWidth: 0,
                marginRight: stackedHero ? 0 : 10 * scale,
                backgroundColor: 'rgba(255,255,255,0.07)',
                borderWidth: 1,
                borderColor: 'rgba(255,255,255,0.14)',
                borderRadius: 16 * scale,
                padding: 12 * scale,
              }}
            >
              <AppText variant="body" style={{ color: '#EDEBFF' }}>
                {heroPrompt}
              </AppText>
              <AppText variant="body" style={{ color: '#9C98C9', marginTop: 8 * scale }}>
                — ELVYN
              </AppText>
            </View>
            <View
              style={{
                alignItems: stackedHero ? 'flex-end' : 'center',
                justifyContent: 'center',
                marginTop: stackedHero ? 8 * scale : 0,
                marginBottom: stackedHero ? -4 * scale : -2 * scale,
              }}
            >
              <ElvynMascot variant="supportive" size={heroMascotSize} />
            </View>
          </View>
        </View>

        {/* Progress */}
        <View
          style={{
            ...card,
            marginTop: -24 * scale,
            flexDirection: 'row',
            alignItems: 'center',
            elevation: 4,
            shadowColor: colors.text,
            shadowOpacity: 0.08,
            shadowRadius: 10,
            shadowOffset: { width: 0, height: 3 },
          }}
        >
          {total > 0 ? (
            <>
              <ProgressRing
                percent={percent}
                size={76 * scale}
                color={colors.primary}
                track={colors.primarySoft}
                textColor={colors.text}
              />
              <View style={{ flex: 1, minWidth: 0, marginLeft: 12 * scale }}>
                <AppText variant="title" style={{ color: colors.text }}>Today's Progress</AppText>
                <AppText variant="body" style={{ color: colors.textMuted, marginTop: 2 * scale }}>
                  {done} of {total} tasks completed
                </AppText>
              </View>
              {remaining > 0 && (
                <Pill label={`${remaining} remaining`} bg={colors.primarySoft} color={colors.primary} scale={scale} />
              )}
            </>
          ) : (
            <View>
              <AppText variant="title" style={{ color: colors.text }}>Today's Progress</AppText>
              <AppText variant="body" style={{ color: colors.textMuted, marginTop: 2 * scale }}>
                No tasks today. A clear day is okay.
              </AppText>
            </View>
          )}
        </View>

        {/* Brain Dump */}
        <TouchableOpacity
          onPress={() => navigation.navigate('BrainDump')}
          accessibilityRole="button"
          accessibilityLabel="Open Brain Dump"
          style={{ ...card, backgroundColor: colors.lavenderSurface, flexDirection: 'row', alignItems: 'center' }}
        >
          <IconTile name="bulb-outline" color={colors.primary} bg={colors.primarySoft} size={tileSize} />
          <View style={{ flex: 1, minWidth: 0, flexShrink: 1, marginLeft: 12 * scale, marginRight: 6 * scale }}>
            <AppText variant="title" style={{ color: colors.text }}>Brain Dump</AppText>
            <AppText variant="body" style={{ color: colors.text, marginTop: 2 * scale }}>
              What's on your mind?
            </AppText>
            <AppText variant="body" style={{ color: colors.textMuted, marginTop: 2 * scale }}>
              Capture ideas, tasks, or anything. Elvyn will help you turn it into action.
            </AppText>
          </View>
          <View
            style={{
              width: 44,
              height: 44,
              flexShrink: 0,
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: colors.primarySoft,
              borderRadius: 999,
              marginLeft: 4 * scale,
            }}
          >
            <Ionicons name="mic-outline" size={20} color={colors.primary} />
          </View>
        </TouchableOpacity>

        {/* Check-in */}
        {checkInStatus?.checkins_enabled && (
          <View style={{ ...card, backgroundColor: colors.warmSurface, borderColor: colors.warmBorder }}>
            <View style={{ flexDirection: 'row', alignItems: 'center' }}>
              <IconTile name="happy-outline" color={colors.accent} bg={colors.surface} size={tileSize} />
              <View style={{ marginLeft: 12 * scale, flex: 1, minWidth: 0 }}>
                <AppText variant="title" style={{ color: colors.text }}>Check-in</AppText>
                <AppText variant="body" style={{ color: colors.textMuted, marginTop: 2 * scale }}>
                  {alreadyCheckedIn
                    ? 'You checked in today. Nice.'
                    : `How are you feeling this ${timeOfDay === 'morning' ? 'morning' : 'evening'}?`}
                </AppText>
              </View>
              {alreadyCheckedIn && <Ionicons name="checkmark-circle" size={26} color={colors.success} />}
            </View>

            {!alreadyCheckedIn && (
              <>
                <View style={{ flexDirection: 'row', gap: 8 * scale, marginTop: 12 * scale }}>
                  {MOODS.map((m) => (
                    <TouchableOpacity
                      key={m.label}
                      disabled={checkingIn}
                      onPress={() => handleQuickMood(m.value)}
                      accessibilityRole="button"
                      accessibilityLabel={`Feeling ${m.label.toLowerCase()}`}
                      style={{
                        flex: 1,
                        flexDirection: 'row',
                        alignItems: 'center',
                        justifyContent: 'center',
                        minHeight: 44,
                        paddingHorizontal: 4 * scale,
                        borderRadius: 14,
                        backgroundColor: colors.surface,
                        borderWidth: 1,
                        borderColor: colors.warmBorder,
                        opacity: checkingIn ? 0.6 : 1,
                      }}
                    >
                      <View style={{ width: 24, height: 24, borderRadius: 12, backgroundColor: colors.warmSurface, alignItems: 'center', justifyContent: 'center', marginRight: 5 * scale }}>
                        <AppText variant="body">{m.emoji}</AppText>
                      </View>
                      <AppText variant="body" style={{ color: colors.text, fontWeight: '500', flexShrink: 1 }}>
                        {m.label}
                      </AppText>
                    </TouchableOpacity>
                  ))}
                </View>
                <TouchableOpacity
                  onPress={() => navigation.navigate('CheckIn', { type: timeOfDay })}
                  accessibilityRole="button"
                  accessibilityLabel="Add more check-in detail"
                  style={{ minHeight: 44, justifyContent: 'center', marginTop: 8 * scale }}
                >
                  <AppText variant="body" style={{ color: colors.primary, fontWeight: '600', flexShrink: 1, textAlign: 'right' }}>
                    Add more detail →
                  </AppText>
                </TouchableOpacity>
              </>
            )}
          </View>
        )}

        {/* Calendar (single entry point) */}
        <TouchableOpacity
          onPress={() => navigation.navigate('Calendar')}
          accessibilityRole="button"
          accessibilityLabel="Open Calendar"
          style={{ ...card, flexDirection: 'row', alignItems: 'center' }}
        >
          <IconTile name="calendar-outline" color={colors.primary} bg={colors.primarySoft} size={tileSize} />
          <View style={{ flex: 1, minWidth: 0, marginLeft: 12 * scale }}>
            <AppText variant="title" style={{ color: colors.text }}>Calendar</AppText>
            <AppText variant="body" style={{ color: colors.textMuted, marginTop: 2 * scale }}>
              Today • {new Date().toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
            </AppText>
          </View>
          <AppText variant="body" style={{ color: colors.primary, fontWeight: '600' }}>
            View calendar →
          </AppText>
        </TouchableOpacity>

        {/* Today's Tasks */}
        <View style={card}>
          <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 6 }}>
            <IconTile name="list-outline" color={colors.primary} bg={colors.primarySoft} size={tileSize} />
            <AppText variant="title" style={{ color: colors.text, flex: 1, minWidth: 0, marginLeft: 12 * scale }}>
              Today's Tasks
            </AppText>
            {remaining > 0 && (
              <Pill label={`${remaining} left`} bg={colors.primarySoft} color={colors.primary} scale={scale} />
            )}
          </View>

          {tasks.length === 0 ? (
            <AppText variant="body" style={{ color: colors.textMuted, paddingVertical: 12 * scale }}>
              No tasks today.
            </AppText>
          ) : (
            tasks.map((item) => <TaskRow key={item.id} task={item} textVariant="body" {...handlers(item)} />)
          )}

          <TouchableOpacity
            onPress={() => navigation.navigate('CreateTask')}
            accessibilityRole="button"
            accessibilityLabel="Create task"
            style={{
              minHeight: 44,
              backgroundColor: colors.primary,
              borderRadius: 14,
              paddingHorizontal: 15 * scale,
              paddingVertical: 12 * scale,
              alignItems: 'center',
              justifyContent: 'center',
              marginTop: 12 * scale,
            }}
          >
            <AppText variant="body" style={{ color: colors.background, fontWeight: '600' }}>+ Create task</AppText>
          </TouchableOpacity>
        </View>

        {/* To-do (no date) */}
        {(undatedTasks.length > 0 || undatedTasksError) && (
          <View style={card}>
            <AppText variant="title" style={{ color: colors.text, marginBottom: 4 * scale }}>
              To-do <AppText variant="body" style={{ color: colors.textMuted }}>(no date)</AppText>
            </AppText>
            {undatedTasksError && (
              <AppText variant="body" style={{ color: colors.textMuted, paddingVertical: 8 * scale }}>
                Couldn't load your to-do list. Pull down to try again.
              </AppText>
            )}
            {undatedTasks.map((item) => (
              <TaskRow key={item.id} task={item} textVariant="body" {...handlers(item)} />
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