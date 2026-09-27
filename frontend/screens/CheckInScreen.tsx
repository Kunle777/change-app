import { useEffect, useMemo, useState } from 'react';
import { Alert, ScrollView, Text, TextInput, TouchableOpacity, View } from 'react-native';
import ElvynMascot from '../components/ElvynMascot';
import { API_BASE_URL } from '../services/api';
import { getAuthHeader } from '../services/supabase';
import { submitFullCheckIn } from '../services/checkins';
import { getCheckInPrompt, getCheckInResponse } from '../utils/elvynCheckInResponse';
import { useColors } from '../theme/colors';

const MOODS = [
  { value: 1, emoji: '😞', label: 'Low' },
  { value: 2, emoji: '😕', label: 'Not great' },
  { value: 3, emoji: '😐', label: 'Okay' },
  { value: 4, emoji: '🙂', label: 'Good' },
  { value: 5, emoji: '😄', label: 'Great' },
];

const GOAL_STATUS_OPTIONS = ['Yes', 'Partially', 'No'];
const REFLECTION_CHIPS = ['Got a lot done', 'Tired', 'Proud of today', 'Struggled'];

type Props = {
  route: { params?: { type?: 'morning' | 'evening' } };
  navigation: any;
};

export default function CheckInScreen({ route, navigation }: Props) {
  const type = route.params?.type ?? 'morning';
  const colors = useColors();
  const [mood, setMood] = useState<number | null>(null);
  const [goalToday, setGoalToday] = useState('');
  const [goalStatus, setGoalStatus] = useState<string | null>(null);
  const [reflectionChip, setReflectionChip] = useState<string | null>(null);
  const [reflectionText, setReflectionText] = useState('');
  const [morningGoal, setMorningGoal] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [response, setResponse] = useState<string | null>(null);
  const checkInPrompt = useMemo(() => getCheckInPrompt(type, mood), [type, mood]);

  useEffect(() => {
    if (type !== 'evening') return;

    let active = true;
    async function fetchMorningGoal() {
      try {
        const res = await fetch(`${API_BASE_URL}/api/checkins/history?limit=10`, {
          headers: await getAuthHeader(),
        });
        if (!res.ok) return;
        const history: { type: string; goal_today?: string; created_at: string }[] = await res.json();
        const today = new Date().toDateString();
        const entry = history.find(
          (checkIn) => checkIn.type === 'morning' && new Date(checkIn.created_at).toDateString() === today && checkIn.goal_today,
        );
        if (active && entry?.goal_today) setMorningGoal(entry.goal_today);
      } catch {
        // Evening check-in remains usable if history is unavailable.
      }
    }

    void fetchMorningGoal();
    return () => {
      active = false;
    };
  }, [type]);

  const reflection = useMemo(
    () => reflectionText.trim() || reflectionChip || undefined,
    [reflectionChip, reflectionText],
  );

  async function handleSubmit() {
    if (mood === null) {
      Alert.alert('Choose a mood', 'Select the option that feels closest today.');
      return;
    }

    setSubmitting(true);
    try {
      await submitFullCheckIn(type, {
        mood,
        ...(type === 'morning' && goalToday.trim() ? { goal_today: goalToday.trim() } : {}),
        ...(type === 'evening' && goalStatus ? { goal_status: goalStatus } : {}),
        ...(type === 'evening' && reflection ? { reflection } : {}),
      });
      setResponse(getCheckInResponse(mood));
    } catch (error) {
      Alert.alert('Could not submit check-in', error instanceof Error ? error.message : 'Please try again.');
    } finally {
      setSubmitting(false);
    }
  }

  if (response) {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', padding: 30, backgroundColor: colors.background }}>
        <ElvynMascot variant={mood !== null && mood <= 2 ? 'supportive' : 'neutral'} size={90} />
        <Text style={{ textAlign: 'center', fontSize: 15, color: colors.text, marginTop: 20, marginBottom: 30 }}>
          {response}
        </Text>
        <TouchableOpacity
          onPress={() => navigation.goBack()}
          style={{ backgroundColor: colors.primary, borderRadius: 10, paddingVertical: 12, paddingHorizontal: 24 }}
        >
          <Text style={{ color: '#fff', fontWeight: '600' }}>Continue to Home →</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.background }}
      contentContainerStyle={{ padding: 20, paddingTop: 28, paddingBottom: 36 }}
      keyboardShouldPersistTaps="handled"
    >
      <TouchableOpacity onPress={() => navigation.goBack()} accessibilityRole="button">
        <Text style={{ color: colors.text }}>← Check-in</Text>
      </TouchableOpacity>
      <Text style={{ fontSize: 11, color: colors.textMuted, marginTop: 8, marginBottom: 20, textTransform: 'capitalize' }}>
        {type}
      </Text>

      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 24 }}>
        <ElvynMascot variant="neutral" size={56} />
        <View style={{ flex: 1 }}>
          <Text style={{ color: colors.text, fontWeight: '600' }}>How are you feeling this {type}?</Text>
          <Text style={{ color: colors.textMuted, fontSize: 12, marginTop: 3 }}>
            There's no right answer. Just check in with yourself.
          </Text>
        </View>
      </View>

      <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 28 }}>
        {MOODS.map((option) => {
          const selected = mood === option.value;
          return (
            <TouchableOpacity
              key={option.value}
              onPress={() => setMood(option.value)}
              accessibilityRole="radio"
              accessibilityState={{ selected }}
              style={{
                alignItems: 'center',
                padding: 8,
                borderRadius: 12,
                borderWidth: 1,
                borderColor: selected ? colors.primary : 'transparent',
                backgroundColor: selected ? `${colors.primary}20` : 'transparent',
              }}
            >
              <Text style={{ fontSize: 26 }}>{option.emoji}</Text>
              <Text style={{ fontSize: 10, color: colors.textMuted, marginTop: 4 }}>{option.label}</Text>
            </TouchableOpacity>
          );
        })}
      </View>

      <View style={{ backgroundColor: colors.surface, borderColor: colors.border, borderWidth: 1, borderRadius: 12, padding: 14, marginBottom: 24 }}>
        <Text style={{ color: colors.textMuted, fontSize: 11, marginBottom: 5 }}>A thought to consider (optional)</Text>
        <Text style={{ color: colors.text, lineHeight: 21 }}>{checkInPrompt}</Text>
      </View>

      {type === 'morning' ? (
        <>
          <Text style={{ color: colors.text, fontWeight: '600', marginBottom: 10 }}>Today's goal (optional)</Text>
          <TextInput
            value={goalToday}
            onChangeText={setGoalToday}
            placeholder="What would you like to focus on?"
            placeholderTextColor={colors.textMuted}
            multiline
            style={{ color: colors.text, backgroundColor: colors.surface, borderColor: colors.border, borderWidth: 1, borderRadius: 10, padding: 12, minHeight: 56, marginBottom: 24, textAlignVertical: 'top' }}
          />
        </>
      ) : (
        <>
          <Text style={{ color: colors.text, fontWeight: '600', marginBottom: 10 }}>
            {morningGoal ? `Did you get to: “${morningGoal}”?` : 'Did you get to your goal today?'}
          </Text>
          <View style={{ flexDirection: 'row', gap: 8, marginBottom: 24 }}>
            {GOAL_STATUS_OPTIONS.map((option) => {
              const selected = goalStatus === option;
              return (
                <TouchableOpacity
                  key={option}
                  onPress={() => setGoalStatus(selected ? null : option)}
                  accessibilityRole="radio"
                  accessibilityState={{ selected }}
                  style={{ paddingVertical: 8, paddingHorizontal: 16, borderRadius: 20, borderWidth: 1, borderColor: selected ? colors.primary : colors.border, backgroundColor: selected ? colors.primary : colors.surface }}
                >
                  <Text style={{ color: selected ? '#fff' : colors.text, fontSize: 13 }}>{option}</Text>
                </TouchableOpacity>
              );
            })}
          </View>

          <Text style={{ color: colors.text, fontWeight: '600', marginBottom: 10 }}>Reflection (optional)</Text>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
            {REFLECTION_CHIPS.map((chip) => {
              const selected = reflectionChip === chip;
              return (
                <TouchableOpacity
                  key={chip}
                  onPress={() => setReflectionChip(selected ? null : chip)}
                  accessibilityRole="checkbox"
                  accessibilityState={{ checked: selected }}
                  style={{ paddingVertical: 8, paddingHorizontal: 12, borderRadius: 16, borderWidth: 1, borderColor: selected ? colors.primary : colors.border, backgroundColor: selected ? `${colors.primary}20` : colors.surface }}
                >
                  <Text style={{ color: colors.text, fontSize: 12 }}>{chip}</Text>
                </TouchableOpacity>
              );
            })}
          </View>
          <TextInput
            value={reflectionText}
            onChangeText={setReflectionText}
            placeholder="Or write your own..."
            placeholderTextColor={colors.textMuted}
            multiline
            style={{ color: colors.text, backgroundColor: colors.surface, borderColor: colors.border, borderWidth: 1, borderRadius: 10, padding: 12, minHeight: 76, marginBottom: 24, textAlignVertical: 'top' }}
          />
        </>
      )}

      <TouchableOpacity
        onPress={handleSubmit}
        disabled={mood === null || submitting}
        style={{ backgroundColor: colors.primary, borderRadius: 10, padding: 16, alignItems: 'center', opacity: mood === null || submitting ? 0.5 : 1 }}
      >
        <Text style={{ color: '#fff', fontWeight: '600' }}>{submitting ? 'Submitting…' : 'Check in'}</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}
