import { useState } from 'react';
import { Alert } from 'react-native';
import TaskActionsSheet from './TaskActionSheet';
import NotNowSheet, { NotNowOption } from './NotNowSheet';
import RescheduleSheet from './RescheduleSheet';
import { cancelTask, completeTask, notNowTask, rescheduleTask } from '../../services/tasks';
import type { Task } from '../../types/task';

type Props = {
  task: Task | null;
  visible: boolean;
  onClose: () => void;
  onChanged: () => void;
  /** Optimistic completion from the parent; falls back to a plain API call. */
  onMarkDone?: (task: Task) => void;
  navigation: any;
};

// Android can't reliably open one Modal while another is still closing.
const MODAL_GAP_MS = 300;

export default function TaskActionsHost({ task, visible, onClose, onChanged, onMarkDone, navigation }: Props) {
  const [notNowVisible, setNotNowVisible] = useState(false);
  const [rescheduleVisible, setRescheduleVisible] = useState(false);

  async function run(fn: () => Promise<unknown>) {
    try {
      await fn();
      onChanged();
    } catch (e) {
      console.log('Task action failed:', e);
      Alert.alert("Couldn't update this task", 'Please try again.');
    }
  }

  function confirmCancel() {
    if (!task) return;
    Alert.alert(
      'Cancel this task?',
      task.series_id ? 'Only this occurrence is cancelled. The repeat continues.' : 'It stays in your history.',
      [
        { text: 'Keep it', style: 'cancel' },
        { text: 'Cancel task', style: 'destructive', onPress: () => void run(() => cancelTask(task.id)) },
      ],
    );
  }

  return (
    <>
      <TaskActionsSheet
        visible={visible}
        onClose={onClose}
        onMarkDone={() => {
          if (!task) return;
          if (onMarkDone) onMarkDone(task);
          else void run(() => completeTask(task.id));
        }}
        onNotNow={() => setTimeout(() => setNotNowVisible(true), MODAL_GAP_MS)}
        onReschedule={() => setTimeout(() => setRescheduleVisible(true), MODAL_GAP_MS)}
        onEdit={() => task && setTimeout(() => navigation.navigate('CreateTask', { taskId: task.id }), 100)}
        onCancel={() => setTimeout(confirmCancel, MODAL_GAP_MS)}
      />
      <NotNowSheet
        visible={notNowVisible}
        onClose={() => setNotNowVisible(false)}
        onPick={(option: NotNowOption) => task && void run(() => notNowTask(task.id, option))}
      />
      <RescheduleSheet
        visible={rescheduleVisible}
        task={task}
        onClose={() => setRescheduleVisible(false)}
        onSave={async (dueDate, reminderTime) => {
          if (!task) return;
          await rescheduleTask(task.id, dueDate, reminderTime);
          onChanged();
        }}
      />
    </>
  );
}