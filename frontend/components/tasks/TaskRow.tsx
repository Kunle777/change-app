import { View, Text, TouchableOpacity } from 'react-native';
import { Task } from '../../types/task';

interface TaskRowProps {
  task: Task;
  onPress: () => void;
  onToggleComplete: () => void;
  onMore: () => void;
}

const PRIORITY_COLOR: Record<string, string> = {
  low: '#10B981',
  medium: '#F59E0B',
  high: '#EF4444',
};

export default function TaskRow({ task, onPress, onToggleComplete, onMore }: TaskRowProps) {
  const isDone = task.status === 'completed';
  const isOverdue =
    task.status === 'pending' && task.due_date && new Date(task.due_date) < new Date();

  return (
    <TouchableOpacity
      onPress={onPress}
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        paddingVertical: 12,
        borderBottomWidth: 1,
        borderBottomColor: '#F1F1F5',
      }}
    >
      <TouchableOpacity
        onPress={onToggleComplete}
        style={{
          width: 22,
          height: 22,
          borderRadius: 11,
          borderWidth: 2,
          borderColor: isDone ? '#10B981' : '#C7C7D1',
          backgroundColor: isDone ? '#10B981' : 'transparent',
          alignItems: 'center',
          justifyContent: 'center',
          marginRight: 12,
        }}
      >
        {isDone && <Text style={{ color: '#fff', fontSize: 12 }}>✓</Text>}
      </TouchableOpacity>

      <View style={{ flex: 1 }}>
        <Text
          style={{
            fontSize: 15,
            fontWeight: '500',
            textDecorationLine: isDone ? 'line-through' : 'none',
            color: isDone ? '#999' : '#111',
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
                backgroundColor: PRIORITY_COLOR[task.priority],
                marginRight: 6,
              }}
            />
          )}
          {task.category && (
            <Text style={{ fontSize: 12, color: '#888', marginRight: 8 }}>{task.category}</Text>
          )}
          {task.reminder_time && (
            <Text style={{ fontSize: 12, color: '#888' }}>
              {new Date(task.reminder_time).toLocaleTimeString([], {
                hour: 'numeric',
                minute: '2-digit',
              })}
            </Text>
          )}
          {isOverdue && (
            <Text style={{ fontSize: 11, color: '#B45309', marginLeft: 8 }}>Overdue</Text>
          )}
        </View>
      </View>

      <TouchableOpacity
        onPress={onToggleComplete}
        accessibilityRole="button"
        accessibilityLabel={isDone ? 'Mark task incomplete' : 'Mark task done'}
        style={{ padding: 6, marginRight: 4 }}
      >
        <Text style={{ fontSize: 20, color: isDone ? '#10B981' : '#4F46E5' }}>
          {isDone ? '✓' : '→'}
        </Text>
      </TouchableOpacity>

      <TouchableOpacity onPress={onMore} style={{ padding: 6 }}>
        <Text style={{ fontSize: 18, color: '#999' }}>⋮</Text>
      </TouchableOpacity>
    </TouchableOpacity>
  );
}
