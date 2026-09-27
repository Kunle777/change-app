import { useEffect, useState, useCallback } from 'react';
import {
  Platform,
  AppState,
  View,
  FlatList,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  RefreshControl,
  Alert,
} from 'react-native';
import DateTimePicker from '@react-native-community/datetimepicker';
import { useNavigation } from '@react-navigation/native';
import { useFocusEffect } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import Svg, { Circle } from 'react-native-svg';
import { RootStackParamList, MainTabParamList } from '../navigation/AppNavigator';

type Nav = NativeStackNavigationProp<
  RootStackParamList & { [K in keyof MainTabParamList]: MainTabParamList[K] }
>;
import TaskRow from '../components/tasks/TaskRow';
import TaskActionsSheet from '../components/tasks/TaskActionSheet';
import { getTasks, createTask, markTaskDone, snoozeTask, cancelTask, parseVoiceTask } from '../services/tasks';
import { updateFcmToken } from '../services/auth';
import { getTodayCheckinStatus } from '../services/checkins';
import { supabase } from '../services/supabase';
import ElvynMascot from '../components/ElvynMascot';
import VoiceCaptureButton from '../components/VoiceCaptureButton';
import type { Task } from '../types/task';
import { useColors, type ThemeColors } from '../theme/colors';
import { recordDailyActivity, type ActivityStreak } from '../services/activity';

type CheckinStatus = {
  checkins_enabled: boolean;
  morning_done: boolean;
  evening_done: boolean;
} | null;

const STREAK_MILESTONES = [3, 7, 30, 100];
const STREAK_RING_SIZE = 72;
const STREAK_RING_RADIUS = 30;
const STREAK_RING_CIRCUMFERENCE = 2 * Math.PI * STREAK_RING_RADIUS;

export default function HomeScreen() {
  const navigation = useNavigation<Nav>();
  const colors = useColors();
  const styles = createStyles(colors);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [newTitle, setnewTitle] = useState('');
  const [taskDueDate, setTaskDueDate] = useState<Date | null>(null);
  const [taskPriority, setTaskPriority] = useState<'low' | 'medium' | 'high'>('medium');
  const [understandingVoice, setUnderstandingVoice] = useState(false);
  const [reminderDate, setReminderDate] = useState<Date | null>(null);
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [showTimePicker, setShowTimePicker] = useState(false);
  const [checkinStatus, setCheckinStatus] = useState<CheckinStatus>(null);
  const [now, setNow] = useState(new Date());
  const [activeTask, setActiveTask] = useState<Task | null>(null);
  const [sheetVisible, setSheetVisible] = useState(false);
  const [repeatFrequency, setRepeatFrequency] = useState<'none' | 'daily' | 'weekly' | 'monthly'>('none');
  const [repeatDays, setRepeatDays] = useState<number[]>([]);
  const [activityStreak, setActivityStreak] = useState<ActivityStreak | null>(null);

  const hour = now.getHours();
  const nextStreakMilestone = activityStreak
    ? STREAK_MILESTONES.find((milestone) => milestone > activityStreak.current_streak)
    : undefined;
  const streakProgressPercent = activityStreak
    ? nextStreakMilestone
      ? Math.min(100, Math.round((activityStreak.current_streak / nextStreakMilestone) * 100))
      : 100
    : 0;

  const loadTasks = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getTasks();
      setTasks(data);
      void recordDailyActivity().then(setActivityStreak).catch(() => {});
      void import('../services/notifications').then(({ reconcileNotifications }) =>
        reconcileNotifications(),
      ).catch((error) => console.warn('Could not refresh local task reminders', error));
    } catch (err) {
      console.log('loadTasks error:', err);
      if (
        (err instanceof Error && err.message.includes('Please log in again')) ||
        (err as any)?.response?.status === 401
      ) {
        await supabase.auth.signOut();
        navigation.reset({ index: 0, routes: [{ name: 'Login' }] });
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      loadTasks();
    }, []),
  );

  useEffect(() => {
    registerForPushNotification();
    import('../services/notifications')
      .then((n) => n.requestNotificationPermissions())
      .catch(() => {});

    let isMounted = true;
    getTodayCheckinStatus()
      .then((data) => {
        if (isMounted) setCheckinStatus(data);
      })
      .catch(() => {
        if (isMounted)
          setCheckinStatus({ checkins_enabled: false, morning_done: false, evening_done: false });
      });

    const subscription = AppState.addEventListener('change', (state) => {
      if (state === 'active') setNow(new Date());
    });

    return () => {
      isMounted = false;
      subscription.remove();
    };
  }, []);

  async function registerForPushNotification() {
    if (Platform.OS === 'web') return;
    try {
      const messagingModule = await import('@react-native-firebase/messaging');
      const messaging = messagingModule.default;
      if (!messaging || typeof messaging !== 'function') return;
      const instance = messaging();
      const authStatus = await instance.requestPermission();
      const enabled =
        authStatus === (messaging as any).AuthorizationStatus?.AUTHORIZED ||
        authStatus === (messaging as any).AuthorizationStatus?.PROVISIONAL;
      if (!enabled) return;
      const token = await instance.getToken();
      if (token) await updateFcmToken(token);
    } catch {
      // silently skip in Expo Go — Firebase requires a native build
    }
  }

  async function handleDone(taskId: string) {
    try {
      await markTaskDone(taskId);
      const n = await import('../services/notifications').catch(() => null);
      if (n && typeof n.cancelTaskReminder === 'function') await n.cancelTaskReminder(taskId);
      setTasks((prev) => prev.filter((t) => t.id !== taskId));
    } catch (err) {
      console.log('handleDone error:', err);
    }
  }

  async function handleSnooze(taskId: string) {
    try {
      const updatedTask = await snoozeTask(taskId);
      if (updatedTask?.reminder_time) {
        const n = await import('../services/notifications').catch(() => null);
        if (n && typeof n.rescheduleTaskReminder === 'function')
          await n.rescheduleTaskReminder(
            taskId,
            updatedTask.title,
            new Date(updatedTask.reminder_time),
          );
      }
      setTasks((prev) => prev.map((t) => (t.id === taskId ? { ...t, ...updatedTask } : t)));
    } catch (err) {
      console.log('handleSnooze error:', err);
    }
  }

  async function handleCreateTask() {
    if (!newTitle.trim() || understandingVoice) return;
    let reminder_time: string | undefined;
    let due_date: string | undefined;
    const dueDateSource = taskDueDate ?? reminderDate ?? (repeatFrequency !== 'none' ? new Date() : null);
    if (dueDateSource) {
      const localDate = new Date(dueDateSource);
      due_date = `${localDate.getFullYear()}-${String(localDate.getMonth() + 1).padStart(2, '0')}-${String(localDate.getDate()).padStart(2, '0')}T00:00:00`;
    }
    if (reminderDate) {
      const iso = reminderDate.toISOString();
      reminder_time = iso;
    }
    try {
      const localStartDate = dueDateSource
        ? `${dueDateSource.getFullYear()}-${String(dueDateSource.getMonth() + 1).padStart(2, '0')}-${String(dueDateSource.getDate()).padStart(2, '0')}`
        : undefined;
      const createdTask = await createTask({
        title: newTitle.trim(),
        priority: taskPriority,
        ...(reminder_time ? { reminder_time } : {}),
        ...(due_date ? { due_date } : {}),
        ...(repeatFrequency !== 'none' && localStartDate
          ? {
              recurrence_rule: {
                frequency: repeatFrequency,
                interval: 1,
                start_date: localStartDate,
                ...(repeatFrequency === 'weekly' ? { days_of_week: repeatDays } : {}),
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'Africa/Lagos',
                ...(reminderDate
                  ? { local_time: `${String(reminderDate.getHours()).padStart(2, '0')}:${String(reminderDate.getMinutes()).padStart(2, '0')}:00` }
                  : {}),
              },
            }
          : {}),
      });
      if (reminder_time && createdTask?.id) {
        try {
          const n = await import('../services/notifications');
          if (typeof n.scheduleTaskReminder === 'function')
            await n.scheduleTaskReminder(
              createdTask.id,
              createdTask.title,
              new Date(reminder_time),
            );
        } catch (err) {
          console.log('scheduleTaskReminder error:', err);
        }
      }
      setnewTitle('');
      setTaskDueDate(null);
      setTaskPriority('medium');
      setRepeatFrequency('none');
      setRepeatDays([]);
      setReminderDate(null);
      loadTasks();
    } catch (err) {
      console.log('createTask error:', err);
    }
  }

  async function handleVoiceTask(transcript: string) {
    setUnderstandingVoice(true);
    try {
      const parsed = await parseVoiceTask(transcript);
      setnewTitle(parsed.title);
      setTaskPriority(parsed.priority);

      const candidateDate = parsed.due_date ? new Date(`${parsed.due_date}T00:00:00`) : null;
      const validDate = candidateDate && !Number.isNaN(candidateDate.getTime()) ? candidateDate : null;
      setTaskDueDate(validDate);

      if (parsed.time) {
        const [hours, minutes] = parsed.time.split(':').map(Number);
        if (Number.isInteger(hours) && hours >= 0 && hours <= 23 && Number.isInteger(minutes) && minutes >= 0 && minutes <= 59) {
          const reminder = validDate ? new Date(validDate) : new Date();
          reminder.setHours(hours, minutes, 0, 0);
          if (reminder.getTime() <= Date.now()) {
            if (validDate) {
              setReminderDate(null);
              Alert.alert(
                'That reminder time has passed',
                'I kept the task and its due date, but cleared the reminder. You can choose a future time before adding it.',
              );
            } else {
              reminder.setDate(reminder.getDate() + 1);
              setReminderDate(reminder);
              const tomorrow = new Date(reminder);
              tomorrow.setHours(0, 0, 0, 0);
              setTaskDueDate(tomorrow);
              Alert.alert(
                'Using tomorrow for the reminder',
                'That time has already passed today, so I set the reminder for its next occurrence. You can change it before adding the task.',
              );
            }
          } else {
            setReminderDate(reminder);
            if (!validDate) {
              const today = new Date(reminder);
              today.setHours(0, 0, 0, 0);
              setTaskDueDate(today);
            }
          }
        } else {
          setReminderDate(null);
        }
      } else {
        setReminderDate(null);
      }
    } catch {
      setnewTitle(transcript);
      Alert.alert('Voice task not interpreted', 'The transcript is in the title field. Add any date or priority details manually.');
    } finally {
      setUnderstandingVoice(false);
    }
  }

  async function refreshTasks() {
    await loadTasks();
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
      <View style={styles.mascotHeader}>
        <ElvynMascot variant="supportive" size={120} />
      </View>
      {checkinStatus?.checkins_enabled && (
        <TouchableOpacity
          style={styles.persistentCheckinIcon}
          onPress={() =>
            navigation.navigate('CheckIn', { type: hour < 12 ? 'morning' : 'evening' })
          }
        >
          <Text style={styles.persistentCheckinIconText}>{hour < 12 ? '🌅' : '🌙'} Check In</Text>
        </TouchableOpacity>
      )}
      {checkinStatus?.checkins_enabled && !checkinStatus.morning_done && hour < 12 && (
        <TouchableOpacity
          style={styles.banner}
          onPress={() => navigation.navigate('CheckIn', { type: 'morning' })}
        >
          <Text style={styles.bannerText}>🌅 Morning check-in ready — tap to start</Text>
          <TouchableOpacity
            onPress={() => setCheckinStatus({ ...checkinStatus, morning_done: true })}
          >
            <Text style={styles.bannerDismiss}>✕</Text>
          </TouchableOpacity>
        </TouchableOpacity>
      )}
      {checkinStatus?.checkins_enabled && !checkinStatus.evening_done && hour >= 12 && (
        <TouchableOpacity
          style={[styles.banner, styles.bannerEvening]}
          onPress={() => navigation.navigate('CheckIn', { type: 'evening' })}
        >
          <Text style={styles.bannerText}>🌙 Evening check-in ready — tap to start</Text>
          <TouchableOpacity
            onPress={() => setCheckinStatus({ ...checkinStatus, evening_done: true })}
          >
            <Text style={styles.bannerDismiss}>✕</Text>
          </TouchableOpacity>
        </TouchableOpacity>
      )}

      <View style={styles.taskTitleRow}>
        <TextInput
          style={[styles.input, styles.taskTitleInput]}
          placeholder="New task.."
          value={newTitle}
          onChangeText={setnewTitle}
          placeholderTextColor={colors.textMuted}
        />
        <VoiceCaptureButton onTranscript={setnewTitle} onFinalTranscript={handleVoiceTask} />
      </View>
      {understandingVoice && <Text style={styles.voiceStatus}>Interpreting task…</Text>}
      {taskPriority !== 'medium' && (
        <Text style={styles.voiceStatus}>Recognized priority: {taskPriority}</Text>
      )}
      <TouchableOpacity style={styles.datePickerButton} onPress={() => setShowDatePicker(true)}>
        <Text style={styles.datePickerText}>
          {taskDueDate ? `📅 ${taskDueDate.toLocaleDateString()}` : '📅 Set date (optional)'}
        </Text>
      </TouchableOpacity>
      <View style={styles.repeatPicker}>
        <Text style={styles.repeatLabel}>Repeat</Text>
        {([
          ['none', 'Does not repeat'],
          ['daily', 'Daily'],
          ['weekly', 'Weekly'],
          ['monthly', 'Monthly'],
        ] as const).map(([value, label]) => (
          <TouchableOpacity
            key={value}
            accessibilityRole="button"
            accessibilityState={{ selected: repeatFrequency === value }}
            onPress={() => {
              setRepeatFrequency(value);
              if (value === 'weekly' && repeatDays.length === 0) {
                setRepeatDays([(taskDueDate ?? reminderDate ?? new Date()).getDay() === 0
                  ? 6
                  : (taskDueDate ?? reminderDate ?? new Date()).getDay() - 1]);
              }
            }}
            style={[styles.repeatOption, repeatFrequency === value && { backgroundColor: colors.primary }]}
          >
            <Text style={{ color: repeatFrequency === value ? colors.surface : colors.text, fontSize: 12 }}>
              {label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
      {repeatFrequency === 'weekly' && (
        <View style={styles.repeatPicker}>
          {['M', 'T', 'W', 'T', 'F', 'S', 'S'].map((label, day) => (
            <TouchableOpacity
              key={`${label}-${day}`}
              accessibilityRole="button"
              accessibilityState={{ selected: repeatDays.includes(day) }}
              onPress={() => setRepeatDays((current) =>
                current.includes(day)
                  ? current.length > 1 ? current.filter((item) => item !== day) : current
                  : [...current, day].sort(),
              )}
              style={[styles.repeatOption, repeatDays.includes(day) && { backgroundColor: colors.primary }]}
            >
              <Text style={{ color: repeatDays.includes(day) ? colors.surface : colors.text }}>{label}</Text>
            </TouchableOpacity>
          ))}
        </View>
      )}
      {reminderDate && (
        <TouchableOpacity style={styles.datePickerButton} onPress={() => setShowTimePicker(true)}>
          <Text style={styles.datePickerText}>
            {`⏰ ${reminderDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`}
          </Text>
        </TouchableOpacity>
      )}
      {(reminderDate || taskDueDate) && (
        <TouchableOpacity onPress={() => { setReminderDate(null); setTaskDueDate(null); }}>
          <Text style={styles.clearDate}>✕ Clear date</Text>
        </TouchableOpacity>
      )}
      {showDatePicker && (
        <DateTimePicker
          value={taskDueDate || reminderDate || new Date()}
          mode="date"
          display={Platform.OS === 'ios' ? 'spinner' : 'default'}
          minimumDate={new Date()}
          onValueChange={(_event, date) => {
            setShowDatePicker(false);
            if (date instanceof Date && !isNaN(date.getTime())) {
              setReminderDate((prev) => {
                const base = prev || new Date();
                const next = new Date(date);
                next.setHours(base.getHours(), base.getMinutes());
                return next;
              });
              const dueDate = new Date(date);
              dueDate.setHours(0, 0, 0, 0);
              setTaskDueDate(dueDate);
            }
          }}
          onDismiss={() => setShowDatePicker(false)}
        />
      )}
      {showTimePicker && (
        <DateTimePicker
          value={reminderDate || new Date()}
          mode="time"
          display={Platform.OS === 'ios' ? 'spinner' : 'default'}
          onValueChange={(_event, time) => {
            setShowTimePicker(false);
            if (time instanceof Date && !isNaN(time.getTime()) && reminderDate) {
              const updated = new Date(reminderDate);
              updated.setHours(time.getHours(), time.getMinutes(), 0, 0);
              setReminderDate(updated);
            }
          }}
          onDismiss={() => setShowTimePicker(false)}
        />
      )}
      <TouchableOpacity
        onPress={handleCreateTask}
        style={[styles.addButton, (!newTitle.trim() || understandingVoice) && styles.addButtonDisabled]}
        disabled={!newTitle.trim() || understandingVoice}
      >
        <Text style={styles.addButtonText}>Add Task</Text>
      </TouchableOpacity>

      <View style={styles.checkinRow}>
        <TouchableOpacity
          style={styles.checkinButton}
          onPress={() => navigation.navigate('CheckIn', { type: 'morning' })}
        >
          <Text style={styles.checkinButtonText}>Morning Check-in</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.checkinButton}
          onPress={() => navigation.navigate('CheckIn', { type: 'evening' })}
        >
          <Text style={styles.checkinButtonText}>Evening Check-in</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.calendarButton}
          onPress={() => navigation.navigate('Calendar')}
        >
          <Text style={styles.calendarButtonText}>📅 Calendar</Text>
        </TouchableOpacity>
      </View>
      {!!activityStreak && (
        <View style={styles.activityStreakCard}>
          <View
            accessible
            accessibilityRole="progressbar"
            accessibilityLabel={`Streak progress: ${streakProgressPercent}%${nextStreakMilestone ? ` toward ${nextStreakMilestone} days` : ', all milestones reached'}`}
            accessibilityValue={{ min: 0, max: 100, now: streakProgressPercent }}
            style={styles.activityStreakRing}
          >
            <Svg width={STREAK_RING_SIZE} height={STREAK_RING_SIZE}>
              <Circle
                cx={STREAK_RING_SIZE / 2}
                cy={STREAK_RING_SIZE / 2}
                r={STREAK_RING_RADIUS}
                fill="none"
                stroke={colors.border}
                strokeWidth={7}
              />
              <Circle
                cx={STREAK_RING_SIZE / 2}
                cy={STREAK_RING_SIZE / 2}
                r={STREAK_RING_RADIUS}
                fill="none"
                stroke={colors.primary}
                strokeWidth={7}
                strokeLinecap="round"
                strokeDasharray={STREAK_RING_CIRCUMFERENCE}
                strokeDashoffset={STREAK_RING_CIRCUMFERENCE * (1 - streakProgressPercent / 100)}
                rotation={-90}
                origin={[STREAK_RING_SIZE / 2, STREAK_RING_SIZE / 2]}
              />
            </Svg>
            <View style={styles.activityStreakRingLabel}>
              <Text style={styles.activityStreakPercent}>{streakProgressPercent}%</Text>
            </View>
          </View>
          <View style={styles.activityStreakCopy}>
            <Text style={styles.activityStreakTitle}>
              {activityStreak.current_streak} day streak · best {activityStreak.longest_streak}
            </Text>
            {nextStreakMilestone ? (
              <Text style={styles.activityStreakHint}>
                {nextStreakMilestone - activityStreak.current_streak} {nextStreakMilestone - activityStreak.current_streak === 1 ? 'day' : 'days'} to your {nextStreakMilestone}-day milestone
              </Text>
            ) : (
              <Text style={styles.activityStreakHint}>You reached every streak milestone. Keep your own pace.</Text>
            )}
          </View>
        </View>
      )}
      <Text style={styles.sectionTitle}>My Tasks</Text>
      <FlatList
        data={tasks}
        keyExtractor={(item) => item.id}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={loadTasks} />}
        renderItem={({ item }) => (
          <TaskRow
            task={item}
            onPress={() => navigation.navigate('TaskDetail', { taskId: item.id })}
            onToggleComplete={() => handleDone(item.id)}
            onMore={() => {
              setActiveTask(item);
              setSheetVisible(true);
            }}
          />
        )}
      />
      <TaskActionsSheet
        visible={sheetVisible}
        onClose={() => setSheetVisible(false)}
        onMarkDone={() => (activeTask ? handleDone(activeTask.id) : Promise.resolve())}
        onNotNow={() => (activeTask ? handleSnooze(activeTask.id) : Promise.resolve())}
        onReschedule={() =>
          activeTask && navigation.navigate('TaskDetail', { taskId: activeTask.id })
        }
        onEdit={() => activeTask && navigation.navigate('TaskDetail', { taskId: activeTask.id })}
        onCancel={() =>
          activeTask
            ? cancelTask(activeTask.id).then(refreshTasks)
            : Promise.resolve()
        }
      />
    </View>
  );
}

const createStyles = (colors: ThemeColors) => StyleSheet.create({
  container: { flex: 1, padding: 20, backgroundColor: colors.background },
  mascotHeader: { alignItems: 'center', height: 140, marginBottom: 8 },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
    backgroundColor: colors.surface,
  },
  taskTitleRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  taskTitleInput: { flex: 1 },
  voiceStatus: { color: colors.textMuted, fontSize: 12, marginBottom: 8 },
  datePickerButton: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
    backgroundColor: colors.surface,
  },
  datePickerText: { color: colors.text },
  clearDate: { color: colors.textMuted, fontSize: 12, marginBottom: 8, textAlign: 'right' },
  addButton: {
    backgroundColor: colors.primary,
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
    marginBottom: 12,
  },
  addButtonText: { color: colors.surface, fontWeight: '600' },
  addButtonDisabled: { opacity: 0.5 },
  checkinRow: { flexDirection: 'row', gap: 8, marginBottom: 16 },
  checkinButton: {
    flex: 1,
    backgroundColor: colors.primaryDeep,
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  checkinButtonText: { color: colors.surface, fontWeight: '600' },
  aiButton: {
    backgroundColor: colors.primaryDeep,
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
    marginBottom: 16,
  },
  aiButtonText: { color: colors.surface, fontWeight: '600' },
  brainDumpButton: {
    backgroundColor: colors.accent,
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
    marginBottom: 16,
  },
  brainDumpButtonText: { color: colors.text, fontWeight: '600' },
  settingsButton: {
    backgroundColor: colors.textMuted,
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
    marginBottom: 16,
  },
  settingsButtonText: { color: colors.surface, fontWeight: '600' },
  sectionTitle: { textAlign: 'center', fontWeight: 'bold', fontSize: 18, marginBottom: 8 },
  banner: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
  },
  bannerEvening: { backgroundColor: colors.surface },
  bannerText: { flex: 1, fontSize: 13, color: colors.text },
  bannerDismiss: { fontSize: 16, color: colors.textMuted, paddingLeft: 8 },
  calendarButton: {
    backgroundColor: colors.surface,
    borderWidth: 1.5,
    borderColor: colors.border,
    padding: 10,
    borderRadius: 8,
    alignItems: 'center',
    marginBottom: 12,
  },
  calendarButtonText: { color: colors.text, fontWeight: '600' },
  persistentCheckinIcon: {
    alignSelf: 'flex-end',
    backgroundColor: colors.surface,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    marginBottom: 8,
  },
  persistentCheckinIconText: {
    fontSize: 12,
    fontWeight: '600',
    color: colors.text,
  },
  repeatPicker: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: 6, marginBottom: 10 },
  repeatLabel: { fontSize: 13, fontWeight: '600', color: colors.textMuted, marginRight: 4 },
  repeatOption: { borderWidth: 1, borderColor: colors.border, borderRadius: 14, paddingHorizontal: 10, paddingVertical: 6 },
  activityStreakCard: { flexDirection: 'row', alignItems: 'center', padding: 12, borderRadius: 12, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, marginBottom: 12 },
  activityStreakRing: { width: STREAK_RING_SIZE, height: STREAK_RING_SIZE, alignItems: 'center', justifyContent: 'center' },
  activityStreakRingLabel: { ...StyleSheet.absoluteFillObject, alignItems: 'center', justifyContent: 'center' },
  activityStreakPercent: { color: colors.text, fontSize: 16, fontWeight: '700' },
  activityStreakCopy: { flex: 1, marginLeft: 12 },
  activityStreakTitle: { color: colors.text, fontSize: 13, fontWeight: '600' },
  activityStreakHint: { color: colors.textMuted, fontSize: 11, marginTop: 3 },
});
