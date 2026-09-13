import { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, ScrollView, ActivityIndicator, Alert } from 'react-native';
import { Task } from '../types/task';
import { getTaskById, breakdownTask } from '../services/tasks';
import { completeTask, notNowTask, rescheduleTask } from '../services/tasks';

type BreakdownStep = { title: string };

export default function TaskDetailScreen({ route, navigation }: any) {
  const { taskId } = route.params;

  const [task, setTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [breakdownLoading, setBreakdownLoading] = useState(false);
  const [steps, setSteps] = useState<BreakdownStep[] | null>(null);
  const [showNotNowOptions, setShowNotNowOptions] = useState(false);

  useEffect(() => {
    loadTask();
  }, [taskId]);

  async function loadTask() {
    setLoading(true);
    try {
      const t = await getTaskById(taskId);
      setTask(t);
    } catch (err) {
      Alert.alert("Couldn't load task", 'Please try again.');
    } finally {
      setLoading(false);
    }
  }

  async function handleMarkDone() {
    setActionLoading('done');
    try {
      const updated = await completeTask(taskId);
      setTask(updated);
      navigation.goBack();
    } catch (err: any) {
      Alert.alert("Couldn't mark this task as done.", '', [
        { text: 'Try again', onPress: handleMarkDone },
        { text: 'Cancel', style: 'cancel' },
      ]);
    } finally {
      setActionLoading(null);
    }
  }

  async function handleNotNow(option: 'later_today' | 'tomorrow') {
    setActionLoading('not_now');
    try {
      const updated = await notNowTask(taskId, option);
      setTask(updated);
      setShowNotNowOptions(false);
      navigation.goBack();
    } catch (err) {
      Alert.alert("Couldn't postpone this task.", 'Please try again.');
    } finally {
      setActionLoading(null);
    }
  }

  async function handleReschedule() {
    // Wire to your existing date/time picker component here —
    // once the user picks a date, call:
    // await rescheduleTask(taskId, newDueDate, newReminderTime)
    navigation.navigate('RescheduleTask', { taskId });
  }

  async function handleBreakdown() {
    setBreakdownLoading(true);
    try {
      const result = await breakdownTask(taskId);
      setSteps(result.steps);
    } catch (err) {
      Alert.alert("Couldn't break this task down.", 'Please try again.');
    } finally {
      setBreakdownLoading(false);
    }
  }

  if (loading || !task) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
        <ActivityIndicator />
      </View>
    );
  }

  const isOverdue =
    task.status === 'pending' && task.due_date && new Date(task.due_date) < new Date();

  return (
    <ScrollView style={{ flex: 1, padding: 20 }}>
      <TouchableOpacity onPress={() => navigation.goBack()}>
        <Text>← Back</Text>
      </TouchableOpacity>

      <Text style={{ fontSize: 22, fontWeight: '700', marginTop: 16 }}>{task.title}</Text>

      {task.category && (
        <View
          style={{
            alignSelf: 'flex-start',
            backgroundColor: '#EEF0FF',
            borderRadius: 12,
            paddingHorizontal: 10,
            paddingVertical: 4,
            marginTop: 8,
          }}
        >
          <Text style={{ fontSize: 12, color: '#4F46E5' }}>{task.category}</Text>
        </View>
      )}

      <View style={{ marginTop: 12 }}>
        {task.due_date && (
          <Text style={{ color: '#666' }}>📅 {new Date(task.due_date).toLocaleDateString()}</Text>
        )}
        {task.reminder_time && (
          <Text style={{ color: '#666', marginTop: 2 }}>
            🕐 {new Date(task.reminder_time).toLocaleTimeString()}
          </Text>
        )}
        {isOverdue && <Text style={{ color: '#B45309', marginTop: 4, fontSize: 12 }}>Overdue</Text>}
      </View>

      {task.description && (
        <View style={{ marginTop: 20 }}>
          <Text style={{ fontWeight: '600', marginBottom: 4 }}>Description</Text>
          <Text style={{ color: '#444' }}>{task.description}</Text>
        </View>
      )}

      <View style={{ marginTop: 20, borderTopWidth: 1, borderTopColor: '#eee', paddingTop: 16 }}>
        <TouchableOpacity onPress={handleBreakdown} disabled={breakdownLoading}>
          <Text style={{ fontWeight: '600' }}>
            {breakdownLoading ? 'Thinking…' : '✨ Make it easier'}
          </Text>
          <Text style={{ color: '#888', fontSize: 12, marginTop: 2 }}>
            Break this task into smaller steps if it feels overwhelming.
          </Text>
        </TouchableOpacity>

        {steps && (
          <View style={{ marginTop: 12 }}>
            {steps.map((s, i) => (
              <Text key={i} style={{ marginBottom: 6 }}>
                ○ {s.title}
              </Text>
            ))}
            <View style={{ flexDirection: 'row', gap: 12, marginTop: 8 }}>
              <TouchableOpacity>
                <Text style={{ color: '#4F46E5', fontWeight: '600' }}>Add all steps</Text>
              </TouchableOpacity>
              <TouchableOpacity>
                <Text style={{ color: '#4F46E5' }}>Add first step</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}
      </View>

      <View style={{ marginTop: 24, borderTopWidth: 1, borderTopColor: '#eee', paddingTop: 16 }}>
        <TouchableOpacity
          onPress={handleMarkDone}
          disabled={actionLoading === 'done'}
          style={{
            backgroundColor: '#4F46E5',
            borderRadius: 10,
            padding: 14,
            alignItems: 'center',
            marginBottom: 10,
          }}
        >
          <Text style={{ color: '#fff', fontWeight: '600' }}>
            {actionLoading === 'done' ? 'Marking done…' : '✓ Mark as done'}
          </Text>
        </TouchableOpacity>

        {!showNotNowOptions ? (
          <TouchableOpacity onPress={() => setShowNotNowOptions(true)} style={{ marginBottom: 10 }}>
            <Text>🕐 Not now</Text>
          </TouchableOpacity>
        ) : (
          <View style={{ marginBottom: 10, gap: 8 }}>
            <Text style={{ color: '#666', fontSize: 12 }}>When should we try again?</Text>
            <TouchableOpacity onPress={() => handleNotNow('later_today')}>
              <Text>Later today</Text>
            </TouchableOpacity>
            <TouchableOpacity onPress={() => handleNotNow('tomorrow')}>
              <Text>Tomorrow</Text>
            </TouchableOpacity>
          </View>
        )}

        <TouchableOpacity onPress={handleReschedule}>
          <Text>📅 Reschedule</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}
