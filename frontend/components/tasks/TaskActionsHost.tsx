import { useEffect, useState } from 'react';
import { Alert } from 'react-native';
import TaskActionSheet, { TaskActionKey } from './TaskActionSheet';
import RescheduleSheet from './RescheduleSheet';
import { cancelTask, notNowTask, rescheduleTask } from '../../services/tasks';
import type { Task } from '../../types/task';

interface Props {
  task: Task | null;
  onClose: () => void;
  onChanged: () => void;
  onMarkDone: (task: Task) => void;
  navigation: any;
}

const MODAL_GAP_MS = 300;
const FRIENDLY_ERROR = "That didn't go through. Please try again in a moment.";

export default function TaskActionsHost({ task, onClose, onChanged, onMarkDone, navigation }: Props) {
  const [current, setCurrent] = useState<Task | null>(null);
  const [sheet, setSheet] = useState<'actions' | 'reschedule' | null>(null);

  useEffect(() => {
    if (task) {
      setCurrent(task);
      setSheet('actions');
    }
  }, [task]);

  function finish() {
    setSheet(null);
    onClose();
  }

  async function run(action: () => Promise<unknown>) {
    try {
      await action();
      onChanged();
    } catch (error) {
      console.log('Task action failed:', error);
      Alert.alert('Something went wrong', FRIENDLY_ERROR);
    }
  }

  function handleSelect(key: TaskActionKey) {
    const selectedTask = current;
    if (!selectedTask) {
      finish();
      return;
    }
    setSheet(null);

    if (key === 'done') {
      onMarkDone(selectedTask);
      onClose();
      return;
    }

    if (key === 'reschedule') {
      setTimeout(() => setSheet('reschedule'), MODAL_GAP_MS);
      return;
    }

    setTimeout(() => {
      if (key === 'edit') {
        onClose();
        navigation.navigate('CreateTask', { taskId: selectedTask.id });
      } else if (key === 'not_now') {
        Alert.alert(
          'Not now',
          'When would you like to see this again?',
          [
            {
              text: 'Later today',
              onPress: () => {
                onClose();
                void run(() => notNowTask(selectedTask.id, 'later_today'));
              },
            },
            {
              text: 'Tomorrow morning',
              onPress: () => {
                onClose();
                void run(() => notNowTask(selectedTask.id, 'tomorrow'));
              },
            },
            { text: 'Never mind', style: 'cancel', onPress: onClose },
          ],
          { cancelable: true, onDismiss: onClose },
        );
      } else if (key === 'cancel') {
        Alert.alert(
          'Cancel this task?',
          selectedTask.has_series
            ? 'Only this occurrence is cancelled. The repeat continues.'
            : 'It stays in your history.',
          [
            { text: 'Keep it', style: 'cancel', onPress: onClose },
            {
              text: 'Cancel task',
              style: 'destructive',
              onPress: () => {
                onClose();
                void run(() => cancelTask(selectedTask.id));
              },
            },
          ],
          { cancelable: true, onDismiss: onClose },
        );
      }
    }, MODAL_GAP_MS);
  }

  return (
    <>
      <TaskActionSheet visible={sheet === 'actions'} onDismiss={finish} onSelect={handleSelect} />
      <RescheduleSheet
        visible={sheet === 'reschedule'}
        task={current}
        onClose={finish}
        onSave={async (dueDate, reminderTime) => {
          if (!current) return;
          await rescheduleTask(current.id, dueDate, reminderTime);
          onChanged();
        }}
      />
    </>
  );
}
