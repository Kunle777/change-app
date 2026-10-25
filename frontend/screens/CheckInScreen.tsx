import { useEffect, useMemo, useState } from 'react';
import { Alert, ScrollView, Text, TextInput, TouchableOpacity, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import ElvynMascot from '../components/ElvynMascot';
import { PrimaryButton } from '../components/auth/Buttons';
import { API_BASE_URL } from '../services/api';
import { getAuthHeader } from '../services/supabase';
import { submitFullCheckIn } from '../services/checkins';
import { getCheckInPrompt, getCheckInResponse } from '../utils/elvynCheckInResponse';
import { useColors } from '../theme/colors';

const MOODS = [
  { value: 5, emoji: '😄', label: 'Great', tint: '#10B981' },
  { value: 4, emoji: '🙂', label: 'Good', tint: '#84CC16' },
  { value: 3, emoji: '😐', label: 'Okay', tint: '#F59E0B' },
  { value: 2, emoji: '🙁', label: 'Not great', tint: '#EF4444' },
  { value: 1, emoji: '😢', label: 'Terrible', tint: '#8B5CF6' },
];

const GOAL_STATUS = [
  { value: 'Yes', icon: 'checkmark-circle', tint: '#10B981' },
  { value: 'Partially', icon: 'ellipse-outline', tint: '#F59E0B' },
  { value: 'No', icon: 'close-circle', tint: '#EF4444' },
] as const;

const REFLECTION_CHIPS = ['Got a lot done', 'Slower day', 'Tired', 'Proud of today', 'Struggled'];

function mascotFor(mood: number | null): 'neutral' | 'supportive' {
  if (mood === null) return 'neutral';
  if (mood >= 4) return 'supportive';
  return 'neutral';
}

type Props = {
  route: { params?: { type?: 'morning' | 'evening' } };
  navigation: any;
};

export default function CheckInScreen({ route, navigation }: Props) {
  const type = route.params?.type ?? 'morning';
  const colors = useColors();
  const insets = useSafeAreaInsets();

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
    (async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/checkins/history?limit=10`, {
          headers: await getAuthHeader(),
        });
        if (!res.ok) return;
        const history: { type: string; goal_today?: string; created_at: string }[] = await res.json();
        const today = new Date().toDateString();
        const entry = history.find(
          (c) => c.type === 'morning' && new Date(c.created_at).toDateString() === today && c.goal_today,
        );
        if (active && entry?.goal_today) setMorningGoal(entry.goal_today);
      } catch {
        // The evening check-in works without the morning goal.
      }
    })();
    return () => {
      active = false;
    };
  }, [type]);

  const reflection = useMemo(
    () => reflectionText.trim() || reflectionChip || undefined,
    [reflectionChip, reflectionText],
  );

  async function handleSubmit() {
    if (mood === null) return;
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
      console.log('Check-in failed:', error);
      Alert.alert("Couldn't save your check-in", 'Please check your connection and try again.');
    } finally {
      setSubmitting(false);
    }
  }

  const isMorning = type === 'morning';
  const card = {
    backgroundColor: colors.surface,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 16,
    marginBottom: 18,
  } as const;
  const heading = { color: colors.text, fontWeight: '700', fontSize: 17 } as const;
  const muted = { color: colors.textMuted, fontSize: 13, marginTop: 4 } as const;

  if (response) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.background, padding: 28, justifyContent: 'center' }}>
        <View style={{ alignItems: 'center' }}>
          <ElvynMascot variant={mascotFor(mood)} size={120} />
          <Text style={{ color: colors.text, fontSize: 17, lineHeight: 25, textAlign: 'center', marginTop: 20, marginBottom: 32 }}>
            {response}
          </Text>
        </View>
        <PrimaryButton label="Back to Home" onPress={() => navigation.goBack()} />
      </View>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.background }}>
      <ScrollView
        keyboardShouldPersistTaps="handled"
        contentContainerStyle={{ paddingBottom: 40 }}
        showsVerticalScrollIndicator={false}
      >
        {/* Hero */}
        <View
          style={{
            backgroundColor: colors.heroBg,
            paddingTop: insets.top + 10,
            paddingHorizontal: 20,
            paddingBottom: 56,
            borderBottomLeftRadius: 32,
            borderBottomRightRadius: 32,
          }}
        >
          <View style={{ flexDirection: 'row', alignItems: 'center' }}>
            <TouchableOpacity onPress={() => navigation.goBack()} hitSlop={12} accessibilityRole="button" accessibilityLabel="Back">
              <Ionicons name="arrow-back" size={24} color="#fff" />
            </TouchableOpacity>
            <Text style={{ color: '#fff', fontSize: 20, fontWeight: '700', marginLeft: 16, flex: 1 }}>Check-in</Text>
            <View
              style={{
                flexDirection: 'row',
                alignItems: 'center',
                backgroundColor: 'rgba(255,255,255,0.1)',
                borderRadius: 999,
                paddingHorizontal: 12,
                paddingVertical: 7,
              }}
            >
              <Ionicons name={isMorning ? 'sunny' : 'moon'} size={16} color={isMorning ? '#FBBF24' : '#C4B5FD'} />
              <Text style={{ color: '#fff', fontSize: 13, fontWeight: '600', marginLeft: 6 }}>
                {isMorning ? 'Morning' : 'Evening'}
              </Text>
            </View>
          </View>

          <View style={{ flexDirection: 'row', alignItems: 'flex-end', marginTop: 22 }}>
            <View style={{ flex: 1, paddingRight: 8, paddingBottom: 6 }}>
              <Text style={{ color: '#fff', fontSize: 28, fontWeight: '800' }}>
                {isMorning ? 'Good morning!' : 'How was your day?'}
              </Text>
              <Text style={{ color: '#D9D6F5', fontSize: 15, lineHeight: 22, marginTop: 6 }}>
                {isMorning ? "Let's set the tone for a great day." : 'Take a moment to reflect.'}
              </Text>
              <Text style={{ color: '#9C98C9', fontSize: 13, marginTop: 10 }}>– ELVYN</Text>
            </View>
            <ElvynMascot variant={mascotFor(mood)} size={118} />
          </View>
        </View>

        <View style={{ paddingHorizontal: 16, marginTop: -30 }}>
          {/* Mood */}
          <View style={card}>
            <Text style={heading}>How are you feeling this {isMorning ? 'morning' : 'evening'}?</Text>
            <Text style={muted}>Pick the mood that fits you best.</Text>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: 16 }}>
              {MOODS.map((m) => {
                const selected = mood === m.value;
                return (
                  <TouchableOpacity
                    key={m.value}
                    onPress={() => setMood(m.value)}
                    accessibilityRole="radio"
                    accessibilityState={{ selected }}
                    accessibilityLabel={m.label}
                    style={{ alignItems: 'center', flex: 1 }}
                  >
                    <View
                      style={{
                        width: 52,
                        height: 52,
                        borderRadius: 26,
                        backgroundColor: `${m.tint}${selected ? '33' : '1A'}`,
                        borderWidth: 2,
                        borderColor: selected ? m.tint : 'transparent',
                        alignItems: 'center',
                        justifyContent: 'center',
                        transform: [{ scale: selected ? 1.08 : 1 }],
                      }}
                    >
                      <Text style={{ fontSize: 26 }}>{m.emoji}</Text>
                    </View>
                    <Text style={{ fontSize: 11, marginTop: 6, color: selected ? colors.text : colors.textMuted, fontWeight: selected ? '700' : '400' }}>
                      {m.label}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>
          </View>

          {isMorning ? (
            <>
              <Text style={{ ...heading, marginBottom: 4, marginLeft: 4 }}>
                Today's goal <Text style={{ color: colors.textMuted, fontWeight: '400', fontSize: 14 }}>(optional)</Text>
              </Text>
              <Text style={{ ...muted, marginLeft: 4, marginTop: 0, marginBottom: 10 }}>
                What's one thing you want to make progress on today?
              </Text>
              <TextInput
                value={goalToday}
                onChangeText={setGoalToday}
                placeholder="e.g. Finish the AI wrapper"
                placeholderTextColor={colors.textMuted}
                multiline
                maxLength={200}
                style={{
                  color: colors.text,
                  backgroundColor: colors.surface,
                  borderColor: colors.border,
                  borderWidth: 1,
                  borderRadius: 16,
                  padding: 14,
                  minHeight: 84,
                  textAlignVertical: 'top',
                  marginBottom: 18,
                }}
              />
            </>
          ) : (
            <>
              <Text style={{ ...heading, marginLeft: 4, marginBottom: 10 }}>
                {morningGoal ? `Did you get to: “${morningGoal}”?` : 'Did you get to your goal today?'}
              </Text>
              <View style={{ flexDirection: 'row', gap: 10, marginBottom: 22 }}>
                {GOAL_STATUS.map((g) => {
                  const selected = goalStatus === g.value;
                  return (
                    <TouchableOpacity
                      key={g.value}
                      onPress={() => setGoalStatus(selected ? null : g.value)}
                      accessibilityRole="radio"
                      accessibilityState={{ selected }}
                      style={{
                        flex: 1,
                        flexDirection: 'row',
                        alignItems: 'center',
                        justifyContent: 'center',
                        paddingVertical: 11,
                        borderRadius: 999,
                        borderWidth: 1.5,
                        borderColor: selected ? g.tint : colors.border,
                        backgroundColor: selected ? `${g.tint}22` : colors.surface,
                      }}
                    >
                      <Ionicons name={g.icon} size={18} color={g.tint} />
                      <Text style={{ color: colors.text, fontWeight: '600', marginLeft: 6 }}>{g.value}</Text>
                    </TouchableOpacity>
                  );
                })}
              </View>

              <Text style={{ ...heading, marginLeft: 4 }}>
                Reflection <Text style={{ color: colors.textMuted, fontWeight: '400', fontSize: 14 }}>(optional)</Text>
              </Text>
              <Text style={{ ...muted, marginLeft: 4, marginBottom: 10 }}>
                What was your day like? Tap a chip or write your own.
              </Text>
              <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
                {REFLECTION_CHIPS.map((chip) => {
                  const selected = reflectionChip === chip;
                  return (
                    <TouchableOpacity
                      key={chip}
                      onPress={() => setReflectionChip(selected ? null : chip)}
                      accessibilityRole="checkbox"
                      accessibilityState={{ checked: selected }}
                      style={{
                        flexDirection: 'row',
                        alignItems: 'center',
                        paddingVertical: 8,
                        paddingHorizontal: 12,
                        borderRadius: 999,
                        borderWidth: 1,
                        borderColor: selected ? colors.primary : colors.border,
                        backgroundColor: selected ? colors.primarySoft : colors.surface,
                      }}
                    >
                      <Ionicons name={selected ? 'checkmark' : 'add'} size={14} color={selected ? colors.primary : colors.textMuted} />
                      <Text style={{ color: colors.text, fontSize: 13, marginLeft: 4 }}>{chip}</Text>
                    </TouchableOpacity>
                  );
                })}
              </View>
              <TextInput
                value={reflectionText}
                onChangeText={setReflectionText}
                placeholder="Or write your own…"
                placeholderTextColor={colors.textMuted}
                multiline
                maxLength={500}
                style={{
                  color: colors.text,
                  backgroundColor: colors.surface,
                  borderColor: colors.border,
                  borderWidth: 1,
                  borderRadius: 16,
                  padding: 14,
                  minHeight: 76,
                  textAlignVertical: 'top',
                  marginBottom: 18,
                }}
              />
            </>
          )}

          {/* Thought for the day */}
          <View style={{ ...card, backgroundColor: colors.lavenderSurface, flexDirection: 'row' }}>
            <Ionicons name="bulb-outline" size={22} color={colors.primary} />
            <View style={{ flex: 1, marginLeft: 12 }}>
              <Text style={{ color: colors.primary, fontWeight: '700', fontSize: 13 }}>A thought to consider (optional)</Text>
              <Text style={{ color: colors.text, fontSize: 14, lineHeight: 21, marginTop: 4 }}>{checkInPrompt}</Text>
            </View>
          </View>

          <PrimaryButton label="Check in" onPress={handleSubmit} loading={submitting} disabled={mood === null} />
          {mood === null && (
            <Text style={{ color: colors.textMuted, fontSize: 12, textAlign: 'center', marginTop: 10 }}>
              Choose a mood to continue.
            </Text>
          )}
        </View>
      </ScrollView>
    </View>
  );
}