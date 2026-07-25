import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';

type Task = {
  id: string;
  title: string;
  priority: string;
  status: string;
  due_date?: string;
};

type TaskCardProps = {
  task: Task;
  onDone: () => void;
  onSnooze: () => void;
};

export default function TaskCard({ task, onDone, onSnooze }: TaskCardProps) {
  const isOverdue =
    task.due_date && new Date(task.due_date) < new Date() && task.status !== 'completed';

  return (
    <View style={[styles.card, isOverdue && styles.overdueCard]}>
      <Text style={styles.title}>{task.title}</Text>
      <Text style={styles.priority}>{task.priority}</Text>

      <TouchableOpacity onPress={onDone} style={styles.doneButton}>
        <Text>Done</Text>
      </TouchableOpacity>

      <TouchableOpacity onPress={onSnooze} style={styles.snoozeButton}>
        <Text>Snooze</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    padding: 12,
    borderRadius: 8,
    backgroundColor: '#fff',
    marginBottom: 8,
    borderWidth: 1,
    borderColor: '#eee',
  },
  overdueCard: { borderColor: 'red', borderWidth: 2 },
  title: { fontSize: 16, fontWeight: '600' },
  priority: { fontSize: 12, color: '#888' },
  doneButton: { marginTop: 8, padding: 8, backgroundColor: '#333', borderRadius: 6 },
  snoozeButton: { marginTop: 4, padding: 8, backgroundColor: '#ccc', borderRadius: 6 },
});
