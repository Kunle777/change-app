import { useEffect, useState } from 'react';
import { ActivityIndicator, Modal, Pressable, Text, TouchableOpacity, View } from 'react-native';
import DateTimePicker from '@react-native-community/datetimepicker';
import { useColors } from '../../theme/colors';
import type { Task } from '../../types/task';

interface Props {
  visible: boolean;
  task: Task | null;
  onClose: () => void;
  onSave: (dueDate: Date, reminderTime?: Date) => Promise<void>;
}

function startOfDay(d: Date) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

export default function RescheduleSheet({ visible, task, onClose, onSave }: Props) {
  const colors = useColors();
  const [date, setDate] = useState<Date>(new Date());
  const [time, setTime] = useState<Date | undefined>(undefined);
  const [showDate, setShowDate] = useState(false);
  const [showTime, setShowTime] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset from the task every time the sheet opens — never keep the previous task's values.
  useEffect(() => {
    if (!visible || !task) return;
    const due = task.due_date ? new Date(task.due_date) : new Date();
    setDate(startOfDay(due) < startOfDay(new Date()) ? new Date() : due);
    setTime(task.reminder_time ? new Date(task.reminder_time) : undefined);
    setShowDate(false);
    setShowTime(false);
    setSaving(false);
    setError(null);
  }, [visible, task?.id]);

  function quick(offsetDays: number) {
    const d = new Date();
    d.setDate(d.getDate() + offsetDays);
    setDate(d);
    setError(null);
  }

  async function handleSave() {
    if (saving) return;
    const day = startOfDay(date);
    if (day < startOfDay(new Date())) {
      setError('Pick today or a day ahead.');
      return;
    }
    // Reminder = the chosen DATE + the chosen clock time (not the old reminder's date).
    const reminder = time
      ? new Date(day.getFullYear(), day.getMonth(), day.getDate(), time.getHours(), time.getMinutes())
      : undefined;
    if (reminder && reminder.getTime() <= Date.now()) {
      setError("That time has already passed. Pick a later time.");
      return;
    }
    const endOfDay = new Date(day.getFullYear(), day.getMonth(), day.getDate(), 23, 59, 59, 999);
    setSaving(true);
    setError(null);
    try {
      await onSave(endOfDay, reminder);
      onClose();
    } catch (e) {
      console.log('Reschedule failed:', e);
      setError("We couldn't save that. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  const field = {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 12,
    padding: 14,
    marginBottom: 14,
  } as const;
  const chip = (label: string, offset: number) => (
    <TouchableOpacity
      key={label}
      onPress={() => quick(offset)}
      style={{ paddingVertical: 8, paddingHorizontal: 14, borderRadius: 20, backgroundColor: colors.primarySoft, marginRight: 8 }}
    >
      <Text style={{ color: colors.primary, fontWeight: '600', fontSize: 13 }}>{label}</Text>
    </TouchableOpacity>
  );

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.4)' }} onPress={onClose}>
        <Pressable
          onPress={(e) => e.stopPropagation()}
          style={{
            marginTop: 'auto',
            backgroundColor: colors.surface,
            borderTopLeftRadius: 24,
            borderTopRightRadius: 24,
            padding: 20,
            paddingBottom: 32,
          }}
        >
          <Text style={{ fontWeight: '700', fontSize: 17, color: colors.text }}>Reschedule</Text>
          <Text style={{ color: colors.textMuted, fontSize: 12, marginTop: 2, marginBottom: 16 }} numberOfLines={1}>
            {task?.title}
          </Text>

          <View style={{ flexDirection: 'row', marginBottom: 14 }}>
            {chip('Today', 0)}
            {chip('Tomorrow', 1)}
            {chip('Next week', 7)}
          </View>

          <Text style={{ fontSize: 12, color: colors.textMuted, marginBottom: 4 }}>Date</Text>
          <TouchableOpacity onPress={() => setShowDate(true)} style={field}>
            <Text style={{ color: colors.text }}>
              {date.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}
            </Text>
          </TouchableOpacity>
          {showDate && (
            <DateTimePicker
              value={date}
              mode="date"
              minimumDate={new Date()}
              onChange={(_, selected) => {
                setShowDate(false);
                if (selected) setDate(selected);
              }}
            />
          )}

          <Text style={{ fontSize: 12, color: colors.textMuted, marginBottom: 4 }}>Reminder time (optional)</Text>
          <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 14 }}>
            <TouchableOpacity onPress={() => setShowTime(true)} style={[field, { flex: 1, marginBottom: 0 }]}>
              <Text style={{ color: time ? colors.text : colors.textMuted }}>
                {time ? time.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }) : 'No reminder'}
              </Text>
            </TouchableOpacity>
            {time && (
              <TouchableOpacity onPress={() => setTime(undefined)} style={{ padding: 12 }}>
                <Text style={{ color: colors.textMuted }}>Clear</Text>
              </TouchableOpacity>
            )}
          </View>
          {showTime && (
            <DateTimePicker
              value={time ?? new Date()}
              mode="time"
              onChange={(_, selected) => {
                setShowTime(false);
                if (selected) setTime(selected);
              }}
            />
          )}

          {error && <Text style={{ color: colors.danger, marginBottom: 10 }}>{error}</Text>}

          <TouchableOpacity
            onPress={handleSave}
            disabled={saving}
            style={{ backgroundColor: colors.primary, borderRadius: 12, padding: 16, alignItems: 'center', marginBottom: 10, opacity: saving ? 0.7 : 1 }}
          >
            {saving ? <ActivityIndicator color="#fff" /> : <Text style={{ color: '#fff', fontWeight: '700' }}>Save</Text>}
          </TouchableOpacity>
          <TouchableOpacity onPress={onClose} style={{ alignItems: 'center', padding: 6 }}>
            <Text style={{ color: colors.textMuted }}>Cancel</Text>
          </TouchableOpacity>
        </Pressable>
      </Pressable>
    </Modal>
  );
}
