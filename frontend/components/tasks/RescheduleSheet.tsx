import { useEffect, useState } from 'react';
import { ActivityIndicator, Modal, View, Text, TouchableOpacity, Pressable } from 'react-native';
import DateTimePicker from '@react-native-community/datetimepicker';
import { Ionicons } from '@expo/vector-icons';
import { Task } from '../../types/task';
import { useColors } from '../../theme/colors';

interface Props {
  visible: boolean;
  task: Task | null;
  onClose: () => void;
  onSave: (dueDate: Date, reminderTime?: Date) => void | Promise<void>;
}

const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate());
const addDays = (d: Date, n: number) => {
  const x = new Date(d);
  x.setDate(x.getDate() + n);
  return x;
};
const sameDay = (a: Date, b: Date) => a.toDateString() === b.toDateString();

export default function RescheduleSheet({ visible, task, onClose, onSave }: Props) {
  const colors = useColors();
  const [date, setDate] = useState<Date>(new Date());
  const [time, setTime] = useState<Date | undefined>();
  const [showDate, setShowDate] = useState(false);
  const [showTime, setShowTime] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset from the task every time the sheet opens (it is mounted before any task is chosen).
  useEffect(() => {
    if (!visible) return;
    const due = task?.due_date ? new Date(task.due_date) : null;
    setDate(due && due >= startOfDay(new Date()) ? due : new Date());
    setTime(task?.reminder_time ? new Date(task.reminder_time) : undefined);
    setError(null);
    setSaving(false);
  }, [visible, task?.id]);

  // The picked time carries its own date, so combine it with the chosen day.
  const reminder = time
    ? new Date(date.getFullYear(), date.getMonth(), date.getDate(), time.getHours(), time.getMinutes())
    : undefined;
  const inPast = !!reminder && reminder.getTime() <= Date.now();

  const today = startOfDay(new Date());
  const chips = [
    { label: 'Today', value: today },
    { label: 'Tomorrow', value: addDays(today, 1) },
    { label: 'Next week', value: addDays(today, 7) },
  ];

  async function handleSave() {
    if (inPast) return;
    setSaving(true);
    setError(null);
    try {
      const endOfDay = new Date(date.getFullYear(), date.getMonth(), date.getDate(), 23, 59, 59, 999);
      await onSave(endOfDay, reminder);
      onClose();
    } catch (e) {
      console.log('Reschedule failed:', e);
      setError("Couldn't reschedule. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  const row = {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 14,
    padding: 14,
    marginBottom: 10,
  } as const;

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.45)' }} onPress={onClose}>
        <Pressable
          onPress={(e) => e.stopPropagation()}
          style={{ marginTop: 'auto', backgroundColor: colors.surface, borderTopLeftRadius: 28, borderTopRightRadius: 28, padding: 20, paddingBottom: 28 }}
        >
          <View style={{ flexDirection: 'row', alignItems: 'center' }}>
            <Ionicons name="calendar-outline" size={24} color={colors.primary} />
            <Text style={{ color: colors.text, fontSize: 18, fontWeight: '800', marginLeft: 10 }}>Reschedule</Text>
          </View>
          <Text style={{ color: colors.textMuted, fontSize: 13, marginTop: 4, marginBottom: 14 }}>
            {task?.series_id ? 'Only this occurrence moves. The repeat stays the same.' : 'Choose a new date and time.'}
          </Text>

          <View style={{ flexDirection: 'row', gap: 8, marginBottom: 14 }}>
            {chips.map((c) => {
              const selected = sameDay(date, c.value);
              return (
                <TouchableOpacity
                  key={c.label}
                  onPress={() => setDate(c.value)}
                  style={{
                    flex: 1,
                    paddingVertical: 9,
                    borderRadius: 999,
                    alignItems: 'center',
                    borderWidth: 1,
                    borderColor: selected ? colors.primary : colors.border,
                    backgroundColor: selected ? colors.primarySoft : 'transparent',
                  }}
                >
                  <Text style={{ color: selected ? colors.primary : colors.text, fontWeight: '600', fontSize: 13 }}>{c.label}</Text>
                </TouchableOpacity>
              );
            })}
          </View>

          <TouchableOpacity style={row} onPress={() => setShowDate(true)}>
            <Ionicons name="calendar-outline" size={20} color={colors.textMuted} />
            <Text style={{ color: colors.textMuted, marginLeft: 10, flex: 1 }}>Date</Text>
            <Text style={{ color: colors.text, fontWeight: '600' }}>
              {date.toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short' })}
            </Text>
          </TouchableOpacity>
          {showDate && (
            <DateTimePicker
              value={date}
              mode="date"
              minimumDate={today}
              onChange={(_, selected) => {
                setShowDate(false);
                if (selected instanceof Date) setDate(selected);
              }}
            />
          )}

          <TouchableOpacity style={row} onPress={() => setShowTime(true)}>
            <Ionicons name="notifications-outline" size={20} color={colors.textMuted} />
            <Text style={{ color: colors.textMuted, marginLeft: 10, flex: 1 }}>Reminder (optional)</Text>
            <Text style={{ color: time ? colors.text : colors.textMuted, fontWeight: '600' }}>
              {time ? time.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }) : 'Add'}
            </Text>
            {time && (
              <TouchableOpacity onPress={() => setTime(undefined)} hitSlop={10} style={{ marginLeft: 10 }}>
                <Ionicons name="close-circle" size={18} color={colors.textMuted} />
              </TouchableOpacity>
            )}
          </TouchableOpacity>
          {showTime && (
            <DateTimePicker
              value={time ?? new Date()}
              mode="time"
              onChange={(_, selected) => {
                setShowTime(false);
                if (selected instanceof Date) setTime(selected);
              }}
            />
          )}

          {inPast && (
            <Text style={{ color: colors.danger, fontSize: 12, marginBottom: 8 }}>
              That reminder time has already passed. Pick a later time or another day.
            </Text>
          )}
          {error && <Text style={{ color: colors.danger, fontSize: 12, marginBottom: 8 }}>{error}</Text>}

          <TouchableOpacity
            onPress={handleSave}
            disabled={saving || inPast}
            style={{ backgroundColor: colors.primary, borderRadius: 14, padding: 16, alignItems: 'center', marginTop: 4, opacity: saving || inPast ? 0.5 : 1 }}
          >
            {saving ? <ActivityIndicator color="#fff" /> : <Text style={{ color: '#fff', fontWeight: '700' }}>Save</Text>}
          </TouchableOpacity>
          <TouchableOpacity onPress={onClose} style={{ alignItems: 'center', marginTop: 14 }}>
            <Text style={{ color: colors.textMuted }}>Cancel</Text>
          </TouchableOpacity>
        </Pressable>
      </Pressable>
    </Modal>
  );
}