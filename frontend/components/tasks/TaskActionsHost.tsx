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
  navigation: any;
};

export default function TaskActionsHost({ task, visible, onClose, onChanged, navigation }: Props) {
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
        onMarkDone={() => task && void run(() => completeTask(task.id))}
        onNotNow={() => setNotNowVisible(true)}
        onReschedule={() => setRescheduleVisible(true)}
        onEdit={() => task && navigation.navigate('CreateTask', { taskId: task.id })}
        onCancel={confirmCancel}
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