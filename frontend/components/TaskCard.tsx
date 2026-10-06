import { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native';
import { breakdownTask } from '../services/tasks';

type Task = {
  id: string;
  title: string;
  priority: string;
  status: string;
  due_date?: string;
  reminder_time?: string;
};

type TaskCardProps = {
  task: Task;
  onDone?: () => Promise<void>;
  onSnooze?: () => Promise<void>;
};

const PRIORITY_LABEL: Record<string, string> = { '1': '🟢 Low', '2': '🟡 Medium', '3': '🔴 High' };

export default function TaskCard({ task, onDone, onSnooze }: TaskCardProps) {
  const [feedback, setFeedback] = useState<{ msg: string; ok: boolean } | null>(null);
  const [loadingDone, setLoadingDone] = useState(false);
  const [loadingSnooze, setLoadingSnooze] = useState(false);
  const [loadingBreakdown, setLoadingBreakdown] = useState(false);
  const [steps, setSteps] = useState<string[] | null>(null);

  const isOverdue =
    task.due_date && new Date(task.due_date) < new Date() && task.status !== '3' && task.status !== 'completed';
  const priorityLabel = PRIORITY_LABEL[String(task.priority)] ?? String(task.priority);

  async function handleDone() {
    if (!onDone) return;
    setLoadingDone(true);
    setFeedback(null);
    try {
      await onDone();
      setFeedback({ msg: '✅ Marked as done', ok: true });
    } catch {
      setFeedback({ msg: '❌ Failed to mark done', ok: false });
    } finally {
      setLoadingDone(false);
    }
  }

  async function handleSnooze() {
    if (!onSnooze) return;
    setLoadingSnooze(true);
    setFeedback(null);
    try {
      await onSnooze();
      setFeedback({ msg: '⏰ Snoozed', ok: true });
    } catch {
      setFeedback({ msg: '❌ Failed to snooze', ok: false });
    } finally {
      setLoadingSnooze(false);
    }
  }

  async function handleBreakdown() {
    setLoadingBreakdown(true);
    setSteps(null);
    setFeedback(null);
    try {
      const result = await breakdownTask(task.id);
      setSteps(result);
    } catch {
      setFeedback({ msg: '❌ Breakdown failed', ok: false });
    } finally {
      setLoadingBreakdown(false);
    }
  }

  return (
    <View style={[styles.card, isOverdue && styles.overdueCard]}>
      <Text style={styles.title}>{task.title}</Text>
      <Text style={styles.priority}>{priorityLabel}</Text>
      {task.reminder_time && (
        <Text style={styles.reminder}>⏰ {new Date(task.reminder_time).toLocaleString()}</Text>
      )}

      {feedback && (
        <Text style={[styles.feedback, feedback.ok ? styles.feedbackOk : styles.feedbackErr]}>
          {feedback.msg}
        </Text>
      )}

      {steps && (
        <View style={styles.stepsContainer}>
          <Text style={styles.stepsTitle}>Breakdown:</Text>
          {steps.map((step, i) => (
            <Text key={i} style={styles.step}>• {step}</Text>
          ))}
        </View>
      )}

      {(onDone || onSnooze) && (
        <View style={styles.buttonRow}>
          {onDone && (
            <TouchableOpacity onPress={handleDone} style={styles.doneButton} disabled={loadingDone}>
              {loadingDone ? <ActivityIndicator size="small" color="#fff" /> : <Text style={styles.btnText}>Done</Text>}
            </TouchableOpacity>
          )}
          {onSnooze && (
            <TouchableOpacity onPress={handleSnooze} style={styles.snoozeButton} disabled={loadingSnooze}>
              {loadingSnooze ? <ActivityIndicator size="small" color="#333" /> : <Text>Snooze</Text>}
            </TouchableOpacity>
          )}
          <TouchableOpacity onPress={handleBreakdown} style={styles.breakdownButton} disabled={loadingBreakdown}>
            {loadingBreakdown ? <ActivityIndicator size="small" color="#fff" /> : <Text style={styles.btnText}>🧩 Break</Text>}
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    padding: 12, borderRadius: 8, backgroundColor: '#fff',
    marginBottom: 8, borderWidth: 1, borderColor: '#eee',
  },
  overdueCard: { borderColor: 'red', borderWidth: 2 },
  title: { fontSize: 16, fontWeight: '600' },
  priority: { fontSize: 12, color: '#888', marginTop: 2 },
  reminder: { fontSize: 12, color: '#555', marginTop: 4 },
  feedback: { marginTop: 6, fontSize: 13, fontWeight: '500' },
  feedbackOk: { color: '#28a745' },
  feedbackErr: { color: '#dc3545' },
  stepsContainer: { marginTop: 8, padding: 8, backgroundColor: '#f8f9fa', borderRadius: 6 },
  stepsTitle: { fontWeight: '600', marginBottom: 4, fontSize: 13 },
  step: { fontSize: 13, color: '#333', marginBottom: 2 },
  buttonRow: { flexDirection: 'row', gap: 8, marginTop: 8 },
  doneButton: { flex: 1, padding: 8, backgroundColor: '#333', borderRadius: 6, alignItems: 'center' },
  snoozeButton: { flex: 1, padding: 8, backgroundColor: '#ccc', borderRadius: 6, alignItems: 'center' },
  breakdownButton: { flex: 1, padding: 8, backgroundColor: '#6f42c1', borderRadius: 6, alignItems: 'center' },
  btnText: { color: '#fff' },
});
