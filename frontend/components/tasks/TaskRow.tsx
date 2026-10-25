import { useEffect, useRef } from 'react';
import { Animated, View, Text, TouchableOpacity } from 'react-native';
import { Task } from '../../types/task';
import { useColors } from '../../theme/colors';
import { isTaskOverdue } from '../../utils/taskDates';

interface TaskRowProps {
  task: Task;
  onPress: () => void;
  onToggleComplete: () => void;
  onMore: () => void;
}

export default function TaskRow({ task, onPress, onToggleComplete, onMore }: TaskRowProps) {
  const colors = useColors();
  const priorityColors: Record<string, string> = {
    low: colors.success,
    medium: colors.accent,
    high: colors.danger,
  };
  const isDone = task.status === 'completed';
  const isOverdue = isTaskOverdue(task.due_date, task.status);
  const scale = useRef(new Animated.Value(1)).current;
  const wasDone = useRef(isDone);
  useEffect(() => {
    if (isDone && !wasDone.current) {
      scale.setValue(0.6);
      Animated.spring(scale, { toValue: 1, friction: 4, tension: 160, useNativeDriver: true }).start();
    }
    wasDone.current = isDone;
  }, [isDone, scale]);

  return (
    <TouchableOpacity
      onPress={onPress}
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        paddingVertical: 12,
        borderBottomWidth: 1,
        borderBottomColor: colors.border,
      }}
    >
      <TouchableOpacity
        onPress={onToggleComplete}
        disabled={isDone}
        hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
        accessibilityRole="button"
        accessibilityLabel={isDone ? 'Task done' : 'Mark task done'}
        style={{
          width: 26,
          height: 26,
          borderRadius: 13,
          borderWidth: 2,
          borderColor: isDone ? colors.success : colors.border,
          backgroundColor: isDone ? colors.success : 'transparent',
          alignItems: 'center',
          justifyContent: 'center',
          marginRight: 12,
        }}
      >
        {isDone && (
          <Animated.Text style={{ color: '#fff', fontSize: 14, fontWeight: '800', transform: [{ scale }] }}>
            ✓
          </Animated.Text>
        )}
      </TouchableOpacity>

      <View style={{ flex: 1 }}>
        <Text
          style={{
            fontSize: 15,
            fontWeight: '500',
            textDecorationLine: isDone ? 'line-through' : 'none',
            color: isDone ? colors.textMuted : colors.text,
          }}
        >
          {task.title}
        </Text>
        <View style={{ flexDirection: 'row', alignItems: 'center', marginTop: 2 }}>
          {task.priority && (
            <View
              style={{
                width: 6,
                height: 6,
                borderRadius: 3,
                backgroundColor: priorityColors[task.priority],
                marginRight: 6,
              }}
            />
          )}
          {task.category && (
            <Text style={{ fontSize: 12, color: colors.textMuted, marginRight: 8 }}>{task.category}</Text>
          )}
          {task.series_id && task.recurrence && (
            <Text style={{ fontSize: 11, color: colors.textMuted, marginRight: 8 }}>
              Repeats {task.recurrence}
            </Text>
          )}
          {task.reminder_time && (
            <Text style={{ fontSize: 12, color: colors.textMuted }}>
              {new Date(task.reminder_time).toLocaleTimeString([], {
                hour: 'numeric',
                minute: '2-digit',
              })}
            </Text>
          )}
          {isOverdue && (
            <Text style={{ fontSize: 11, color: colors.danger, marginLeft: 8 }}>Overdue</Text>
          )}
        </View>
      </View>

      <TouchableOpacity onPress={onMore} style={{ padding: 6 }}>
        <Text style={{ fontSize: 18, color: colors.textMuted }}>⋮</Text>
      </TouchableOpacity>
    </TouchableOpacity>
  );
}
