import { useCallback, useRef } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import { Alert } from 'react-native';
import { completeTask } from '../services/tasks';
import type { Task } from '../types/task';

type TaskSetter = Dispatch<SetStateAction<Task[]>>;

/**
 * Optimistic completion: the tick shows instantly, the API call runs in the
 * background, and on failure the task is put back with a calm message.
 * There is no reopen endpoint, so this only ever completes (never un-completes).
 */
export function useTaskCompletion(setters: TaskSetter[], onSettled: () => void) {
  const inFlight = useRef(new Set<string>());

  const setStatus = useCallback(
    (id: string, status: Task['status']) => {
      setters.forEach((set) =>
        set((prev) => prev.map((t) => (t.id === id ? { ...t, status } : t))),
      );
    },
    // setters are stable useState setters
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  return useCallback(
    async (task: Task) => {
      if (task.status === 'completed' || inFlight.current.has(task.id)) return;
      inFlight.current.add(task.id);
      const previous = task.status;
      setStatus(task.id, 'completed');
      try {
        await completeTask(task.id);
      } catch (error) {
        console.log('Complete task failed:', error);
        setStatus(task.id, previous);
        Alert.alert("That didn't save", "We've put the task back. Please try again in a moment.");
      } finally {
        inFlight.current.delete(task.id);
        onSettled();
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [onSettled],
  );
}
