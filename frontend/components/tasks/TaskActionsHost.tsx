import { useEffect, useState } from 'react';
import { Alert } from 'react-native';
import TaskActionSheet, { TaskActionKey } from './TaskActionSheet';
import RescheduleSheet from './RescheduleSheet';
import { cancelTask, notNowTask, rescheduleTask } from '../../services/tasks';
import type { Task } from '../../types/task';

interface Props {
  /** Set to open the actions for this task; set back to null when onClose fires. */
  task: Task | null;
  onClose: () => void;
  onChanged: () => void;
  onMarkDone: (task: Task) => void;
  navigation: any;
}

// Android can't reliably open one Modal while another is still closing.
const MODAL_GAP_MS = 300;

const FRIENDLY = "That didn't go through. Please try again in a moment.";

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

  async function run(fn: () => Promise<unknown>) {
    try {
      await fn();
      onChanged();
    } catch (error) {
      console.log('Task action failed:', error);
      Alert.alert('Something went wrong', FRIENDLY);
    }
  }

  function handleSelect(key: TaskActionKey) {
    const t = current;
    if (!t) return finish();
    setSheet(null);

    if (key === 'done') {
      onMarkDone(t);
      return onClose();
    }
    if (key === 'reschedule') {
      setTimeout(() => setSheet('reschedule'), MODAL_GAP_MS);
      return;
    }
    // Everything else runs after the sheet has fully closed.
    setTimeout(() => {
      if (key === 'edit') {
        onClose();
        navigation.navigate('CreateTask', { taskId: t.id });
      } else if (key === 'not_now') {
        Alert.alert('Not now', 'When would you like to see this again?', [
          { text: 'Later today', onPress: () => { onClose(); run(() => notNowTask(t.id, 'later_today')); } },
          { text: 'Tomorrow morning', onPress: () => { onClose(); run(() => notNowTask(t.id, 'tomorrow')); } },
          { text: 'Never mind', style: 'cancel', onPress: onClose },
        ], { cancelable: true, onDismiss: onClose });
      } else if (key === 'cancel') {
        Alert.alert('Cancel this task?', "It will be removed from your list.", [
          { text: 'Keep it', style: 'cancel', onPress: onClose },
          { text: 'Cancel task', style: 'destructive', onPress: () => { onClose(); run(() => cancelTask(t.id)); } },
        ], { cancelable: true, onDismiss: onClose });
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
