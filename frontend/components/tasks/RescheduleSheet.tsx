import { useState } from 'react';
import { Modal, View, Text, TouchableOpacity, Pressable } from 'react-native';
import DateTimePicker from '@react-native-community/datetimepicker';
import { Task } from '../../types/task';

interface RescheduleSheetProps {
  visible: boolean;
  task: Task | null;
  onClose: () => void;
  onSave: (dueDate: Date, reminderTime?: Date) => void;
}

export default function RescheduleSheet({ visible, task, onClose, onSave }: RescheduleSheetProps) {
  const [date, setDate] = useState<Date>(task?.due_date ? new Date(task.due_date) : new Date());
  const [time, setTime] = useState<Date | undefined>(
    task?.reminder_time ? new Date(task.reminder_time) : undefined,
  );
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [showTimePicker, setShowTimePicker] = useState(false);

  function handleSave() {
    onSave(date, time);
    onClose();
  }

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.4)' }} onPress={onClose}>
        <Pressable
          onPress={(e) => e.stopPropagation()}
          style={{
            marginTop: 'auto',
            backgroundColor: '#fff',
            borderTopLeftRadius: 20,
            borderTopRightRadius: 20,
            padding: 20,
            paddingBottom: 32,
          }}
        >
          <Text style={{ fontWeight: '700', fontSize: 16 }}>Reschedule</Text>
          <Text style={{ color: '#888', fontSize: 12, marginTop: 2, marginBottom: 20 }}>
            Choose a new date and time
          </Text>

          <Text style={{ fontSize: 12, color: '#888', marginBottom: 4 }}>Date</Text>
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
            <Text>{date.toLocaleDateString()}</Text>
          </TouchableOpacity>
          {showDatePicker && (
            <DateTimePicker
              value={date}
              mode="date"
              onChange={(_, selected) => {
                setShowDatePicker(false);
                if (selected instanceof Date) setDate(selected);
              }}
            />
          )}

          <Text style={{ fontSize: 12, color: '#888', marginBottom: 4 }}>Time</Text>
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
            <Text style={{ color: time ? '#111' : '#999' }}>
              {time
                ? time.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
                : 'Select time'}
            </Text>
          </TouchableOpacity>
          {showTimePicker && (
            <DateTimePicker
              value={time ?? new Date()}
              mode="time"
              onChange={(_, selected) => {
                setShowTimePicker(false);
                if (selected instanceof Date) setTime(selected);
              }}
            />
          )}

          <Text style={{ fontSize: 12, color: '#888', marginBottom: 4 }}>Reminder (optional)</Text>
          <View
            style={{
              borderWidth: 1,
              borderColor: '#ddd',
              borderRadius: 10,
              padding: 12,
              marginBottom: 24,
            }}
          >
            <Text style={{ color: '#999' }}>
              {time
                ? `Reminds you at ${time.toLocaleTimeString([], {
                    hour: 'numeric',
                    minute: '2-digit',
                  })}`
                : 'Add reminder'}
            </Text>
          </View>

          <TouchableOpacity
            onPress={handleSave}
            style={{
              backgroundColor: '#4F46E5',
              borderRadius: 10,
              padding: 16,
              alignItems: 'center',
              marginBottom: 10,
            }}
          >
            <Text style={{ color: '#fff', fontWeight: '600' }}>Save</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={onClose} style={{ alignItems: 'center' }}>
            <Text style={{ color: '#888' }}>Cancel</Text>
          </TouchableOpacity>
        </Pressable>
      </Pressable>
    </Modal>
  );
}
