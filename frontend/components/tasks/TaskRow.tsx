import { useEffect, useRef } from 'react';
import { Animated, View, Text, TouchableOpacity } from 'react-native';
import type { ReactNode } from 'react';
import type { StyleProp, TextProps, TextStyle } from 'react-native';
import { Task } from '../../types/task';
import { useColors } from '../../theme/colors';
import { isTaskOverdue } from '../../utils/taskDates';
import AppText from '../ui/AppText';
import type { TypographyVariant } from '../../theme/typography';

interface TaskRowProps {
  task: Task;
  onPress: () => void;
  onToggleComplete: () => void;
  onMore: () => void;
  textVariant?: TypographyVariant;
}

interface TaskRowTextProps extends TextProps {
  variant?: TypographyVariant;
  style?: StyleProp<TextStyle>;
  children: ReactNode;
}

function TaskRowText({ variant, style, children, ...props }: TaskRowTextProps) {
  return variant ? (
    <AppText variant={variant} style={style} {...props}>
      {children}
    </AppText>
  ) : (
    <Text style={style} {...props}>
      {children}
    </Text>
  );
}

export default function TaskRow({ task, onPress, onToggleComplete, onMore, textVariant }: TaskRowProps) {
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
      accessibilityRole={textVariant ? 'button' : undefined}
      accessibilityLabel={textVariant ? `Open task: ${task.title}` : undefined}
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        minHeight: textVariant ? 44 : undefined,
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
          width: textVariant ? 44 : 26,
          height: textVariant ? 44 : 26,
          borderRadius: textVariant ? 22 : 13,
          borderWidth: 2,
          borderColor: isDone ? colors.success : colors.border,
          backgroundColor: isDone ? colors.success : 'transparent',
          alignItems: 'center',
          justifyContent: 'center',
          marginRight: textVariant ? 4 : 12,
        }}
      >
        {isDone && (
          <Animated.Text
            allowFontScaling
            maxFontSizeMultiplier={textVariant ? 1.2 : undefined}
            style={{ color: '#fff', fontSize: 14, fontWeight: '800', transform: [{ scale }] }}
          >
            ✓
          </Animated.Text>
        )}
      </TouchableOpacity>

      <View style={{ flex: 1 }}>
        <TaskRowText
          variant={textVariant}
          style={[
            textVariant ? null : { fontSize: 15 },
            {
              fontWeight: '500',
              textDecorationLine: isDone ? 'line-through' : 'none',
              color: isDone ? colors.textMuted : colors.text,
            },
          ]}
        >
          {task.title}
        </TaskRowText>
        <View
          style={{
            flexDirection: 'row',
            flexWrap: textVariant ? 'wrap' : 'nowrap',
            alignItems: 'center',
            marginTop: 2,
          }}
        >
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
            <TaskRowText
              variant={textVariant ? 'body' : undefined}
              style={[textVariant ? null : { fontSize: 12 }, { color: colors.textMuted, marginRight: 8 }]}
            >
              {task.category}
            </TaskRowText>
          )}
          {task.has_series && task.recurrence && (
            <TaskRowText
              variant={textVariant ? 'body' : undefined}
              style={[textVariant ? null : { fontSize: 11 }, { color: colors.textMuted, marginRight: 8 }]}
            >
              Repeats {task.recurrence}
            </TaskRowText>
          )}
          {task.reminder_time && (
            <TaskRowText
              variant={textVariant ? 'body' : undefined}
              style={[textVariant ? null : { fontSize: 12 }, { color: colors.textMuted }]}
            >
              {new Date(task.reminder_time).toLocaleTimeString([], {
                hour: 'numeric',
                minute: '2-digit',
              })}
            </TaskRowText>
          )}
          {isOverdue && (
            <TaskRowText
              variant={textVariant ? 'body' : undefined}
              style={[textVariant ? null : { fontSize: 11 }, { color: colors.danger, marginLeft: 8 }]}
            >
              Overdue
            </TaskRowText>
          )}
        </View>
      </View>

      <TouchableOpacity
        onPress={onMore}
        accessibilityRole={textVariant ? 'button' : undefined}
        accessibilityLabel={textVariant ? `More actions for ${task.title}` : undefined}
        style={
          textVariant
            ? { width: 44, height: 44, alignItems: 'center', justifyContent: 'center' }
            : { padding: 6 }
        }
      >
        <TaskRowText
          variant={textVariant ? 'title' : undefined}
          style={[textVariant ? null : { fontSize: 18 }, { color: colors.textMuted, lineHeight: 24 }]}
        >
          ⋮
        </TaskRowText>
      </TouchableOpacity>
    </TouchableOpacity>
  );
}
