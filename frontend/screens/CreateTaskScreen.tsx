import { useState, useEffect } from 'react';
import { View, Text, TextInput, TouchableOpacity, ScrollView, Alert, Modal } from 'react-native';
import DateTimePicker from '@react-native-community/datetimepicker';
import { createTask, updateTask, getTaskById } from '../services/tasks';
import { TaskPriority, TaskRecurrence } from '../types/task';

const PRIORITIES: TaskPriority[] = ['low', 'medium', 'high'];
const RECURRENCE_OPTIONS: { value: TaskRecurrence; label: string }[] = [
  { value: 'none', label: 'Does not repeat' },
  { value: 'daily', label: 'Every day' },
  { value: 'weekly', label: 'Every week' },
  { value: 'monthly', label: 'Every month' },
];

export default function CreateTaskScreen({ route, navigation }: any) {
  const taskId: string | undefined = route.params?.taskId;
  const prefilledDate: Date | undefined = route.params?.prefilledDate
    ? new Date(route.params.prefilledDate)
    : undefined;
  const isEdit = !!taskId;

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState<TaskPriority>('medium');
  const [dueDate, setDueDate] = useState<Date | undefined>(prefilledDate);
  const [reminderTime, setReminderTime] = useState<Date | undefined>();
  const [recurrence, setRecurrence] = useState<TaskRecurrence>('none');

  const [showDatePicker, setShowDatePicker] = useState(false);
  const [showTimePicker, setShowTimePicker] = useState(false);
  const [showRecurrenceModal, setShowRecurrenceModal] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (isEdit) loadExistingTask();
  }, [taskId]);

  async function loadExistingTask() {
    try {
      const task = await getTaskById(taskId!);
      setTitle(task.title);
      setDescription(task.description ?? '');
      setPriority(task.priority);
      setDueDate(task.due_date ? new Date(task.due_date) : undefined);
      setReminderTime(task.reminder_time ? new Date(task.reminder_time) : undefined);
      setRecurrence((task.recurrence as TaskRecurrence) ?? 'none');
    } catch {
      Alert.alert("Couldn't load task", 'Please try again.');
    }
  }

  function onDateChange(_: any, selected?: Date) {
    setShowDatePicker(false);
    if (selected instanceof Date) setDueDate(selected);
  }

  function onTimeChange(_: any, selected?: Date) {
    setShowTimePicker(false);
    if (selected instanceof Date) setReminderTime(selected);
  }

  async function handleSave() {
    if (!title.trim()) {
      Alert.alert('Title required', 'Give the task a title before saving.');
      return;
    }
    setSaving(true);
    try {
      const payload = {
        title: title.trim(),
        description: description.trim() || undefined,
        priority,
        due_date: dueDate?.toISOString(),
        reminder_time: reminderTime?.toISOString(),
        recurrence: recurrence === 'none' ? undefined : recurrence,
      };
      if (isEdit) {
        await updateTask(taskId!, payload);
      } else {
        await createTask(payload);
      }
      navigation.goBack();
    } catch (err: any) {
      Alert.alert("Couldn't save task", err.message ?? 'Please try again.');
    } finally {
      setSaving(false);
    }
  }

  const recurrenceLabel =
    RECURRENCE_OPTIONS.find((r) => r.value === recurrence)?.label ?? 'Does not repeat';

  return (
    <ScrollView style={{ flex: 1, padding: 20 }}>
      <TouchableOpacity onPress={() => navigation.goBack()}>
        <Text>← Cancel</Text>
      </TouchableOpacity>

      <Text style={{ fontSize: 20, fontWeight: '700', marginTop: 16, marginBottom: 20 }}>
        {isEdit ? 'Edit Task' : 'Create Task'}
      </Text>

      <Text style={{ fontSize: 12, color: '#888', marginBottom: 4 }}>Task title *</Text>
      <TextInput
        value={title}
        onChangeText={setTitle}
        placeholder="e.g. Finish portfolio website"
        style={{
          borderWidth: 1,
          borderColor: '#ddd',
          borderRadius: 10,
          padding: 12,
          marginBottom: 16,
        }}
      />

      <Text style={{ fontSize: 12, color: '#888', marginBottom: 4 }}>Description (optional)</Text>
      <TextInput
        value={description}
        onChangeText={setDescription}
        placeholder="Add more details..."
        multiline
        style={{
          borderWidth: 1,
          borderColor: '#ddd',
          borderRadius: 10,
          padding: 12,
          minHeight: 70,
          marginBottom: 16,
          textAlignVertical: 'top',
        }}
      />

      <Text style={{ fontSize: 12, color: '#888', marginBottom: 6 }}>Priority</Text>
      <View style={{ flexDirection: 'row', gap: 8, marginBottom: 16 }}>
        {PRIORITIES.map((p) => (
          <TouchableOpacity
            key={p}
            onPress={() => setPriority(p)}
            style={{
              flex: 1,
              paddingVertical: 10,
              borderRadius: 10,
              borderWidth: 1,
              borderColor: priority === p ? '#4F46E5' : '#ddd',
              backgroundColor: priority === p ? '#EEF0FF' : '#fff',
              alignItems: 'center',
            }}
          >
            <Text style={{ textTransform: 'capitalize' }}>{p}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <Text style={{ fontSize: 12, color: '#888', marginBottom: 4 }}>Due date (optional)</Text>
      <TouchableOpacity
        onPress={() => setShowDatePicker(true)}
        style={{
          borderWidth: 1,
          borderColor: '#ddd',
          borderRadius: 10,
          padding: 12,
          marginBottom: 16,
        }}
      >
        <Text style={{ color: dueDate ? '#111' : '#999' }}>
          {dueDate ? dueDate.toLocaleDateString() : 'Select date'}
        </Text>
      </TouchableOpacity>
      {showDatePicker && (
        <DateTimePicker value={dueDate ?? new Date()} mode="date" onChange={onDateChange} />
      )}

      <Text style={{ fontSize: 12, color: '#888', marginBottom: 4 }}>Reminder (optional)</Text>
      <TouchableOpacity
        onPress={() => setShowTimePicker(true)}
        style={{
          borderWidth: 1,
          borderColor: '#ddd',
          borderRadius: 10,
          padding: 12,
          marginBottom: 16,
        }}
      >
        <Text style={{ color: reminderTime ? '#111' : '#999' }}>
          {reminderTime
            ? reminderTime.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
            : 'Select time'}
        </Text>
      </TouchableOpacity>
      {showTimePicker && (
        <DateTimePicker value={reminderTime ?? new Date()} mode="time" onChange={onTimeChange} />
      )}

      <Text style={{ fontSize: 12, color: '#888', marginBottom: 4 }}>Repeat (optional)</Text>
      <TouchableOpacity
        onPress={() => setShowRecurrenceModal(true)}
        style={{
          borderWidth: 1,
          borderColor: '#ddd',
          borderRadius: 10,
          padding: 12,
          marginBottom: 24,
        }}
      >
        <Text>{recurrenceLabel}</Text>
      </TouchableOpacity>

      <Modal visible={showRecurrenceModal} transparent animationType="slide">
        <TouchableOpacity
          style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.4)' }}
          onPress={() => setShowRecurrenceModal(false)}
        >
          <View
            style={{
              marginTop: 'auto',
              backgroundColor: '#fff',
              borderTopLeftRadius: 20,
              borderTopRightRadius: 20,
              paddingBottom: 24,
            }}
          >
            {RECURRENCE_OPTIONS.map((opt) => (
              <TouchableOpacity
                key={opt.value}
                onPress={() => {
                  setRecurrence(opt.value);
                  setShowRecurrenceModal(false);
                }}
                style={{ padding: 16, borderTopWidth: 1, borderTopColor: '#F1F1F5' }}
              >
                <Text style={{ fontWeight: opt.value === recurrence ? '700' : '400' }}>
                  {opt.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </TouchableOpacity>
      </Modal>

      <TouchableOpacity
        onPress={handleSave}
        disabled={saving}
        style={{
          backgroundColor: '#4F46E5',
          borderRadius: 10,
          padding: 16,
          alignItems: 'center',
          opacity: saving ? 0.6 : 1,
        }}
      >
        <Text style={{ color: '#fff', fontWeight: '600' }}>{saving ? 'Saving…' : 'Save task'}</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}
