import React, { useEffect, useState, useMemo } from 'react';
import {
  View,
  Text,
  TextInput,
  Button,
  StyleSheet,
  Alert,
  TouchableOpacity,
  ScrollView,
} from 'react-native';
import MoodPicker from '../components/MoodPicker';
import { submitMorningCheckin, submitEveningCheckin } from '../services/checkins';
import { API_BASE_URL } from '../services/api';
import { getAuthHeader } from '../services/supabase';
import {
  MORNING_PROMPTS,
  ANTI_PROCRASTINATION_PROMPTS,
  EVENING_LOW_MOOD_PROMPTS,
  EVENING_FINE_MOOD_PROMPTS,
} from '../data/prompts';

const REFLECTION_CHIPS = ['Got a lot done', 'Slower day', 'Tired', 'Proud of today', 'Struggled'];

const MORNING_POOL = [...MORNING_PROMPTS, ...ANTI_PROCRASTINATION_PROMPTS];
const todaysPrompt = MORNING_POOL[new Date().getDate() % MORNING_POOL.length];

type Props = {
  route: { params: { type: 'morning' | 'evening' } };
  navigation: any;
};

export default function CheckInScreen({ route, navigation }: Props) {
  const { type } = route.params;
  const [mood, setMood] = useState<number | null>(null);
  const [goalText, setGoalText] = useState('');
  const [goalStatus, setGoalStatus] = useState<string | null>(null);
  const [reflectionText, setReflectionText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [morningGoal, setMorningGoal] = useState<string | null>(null);

  useEffect(() => {
    if (type === 'evening') fetchMorningGoal();
  }, []);

  async function fetchMorningGoal() {
    try {
      const res = await fetch(`${API_BASE_URL}/api/checkins/history?limit=5`, {
        headers: await getAuthHeader(),
      });
      if (!res.ok) return;
      const history: { type: string; goal_today?: string; created_at: string }[] = await res.json();
      const todayStr = new Date().toISOString().slice(0, 10);
      const morningEntry = history.find(
        (c) => c.type === 'morning' && c.created_at.startsWith(todayStr) && c.goal_today,
      );
      if (morningEntry?.goal_today) setMorningGoal(morningEntry.goal_today);
    } catch {}
  }

  const handleReflectionChip = (chip: string) => {
    setReflectionText((prev) => (prev ? `${prev} • ${chip}` : chip));
  };

  const eveningPrompt = useMemo(() => {
    if (mood === null) return null;
    const pool = mood <= 2 ? EVENING_LOW_MOOD_PROMPTS : EVENING_FINE_MOOD_PROMPTS;
    return pool[new Date().getDate() % pool.length];
  }, [mood]);

  const handleSubmit = async () => {
    if (mood === null) {
      Alert.alert('Pick a mood first');
      return;
    }
    setSubmitting(true);
    try {
      if (type === 'morning') {
        await submitMorningCheckin(mood, goalText);
      } else {
        await submitEveningCheckin(mood, reflectionText, goalStatus);
      }
      navigation.goBack();
    } catch (err) {
      Alert.alert('Something went wrong', String(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>{type === 'morning' ? 'Morning Check-In' : 'Evening Review'}</Text>

      <Text style={styles.label}>How are you feeling?</Text>
      <MoodPicker selected={mood} onSelect={setMood} />

      {type === 'morning' && (
        <>
          <Text style={styles.label}>Today's goal (optional)</Text>
          <View style={styles.courageBox}>
            <Text style={styles.couragePrompt}>💡 {todaysPrompt}</Text>
          </View>
          <TextInput
            style={styles.input}
            value={goalText}
            onChangeText={setGoalText}
            placeholder="e.g. Finish the AI wrapper"
            multiline
          />
        </>
      )}

      {type === 'evening' && (
        <>
          {eveningPrompt && (
            <View style={styles.courageBox}>
              <Text style={styles.couragePrompt}>💡 {eveningPrompt}</Text>
            </View>
          )}

          {morningGoal && (
            <View style={styles.section}>
              <Text style={styles.label}>Did you get to: "{morningGoal}"?</Text>
              <View style={styles.row}>
                {['Yes', 'Partially', 'No'].map((opt) => (
                  <TouchableOpacity
                    key={opt}
                    onPress={() => setGoalStatus(opt)}
                    style={[styles.chip, goalStatus === opt && styles.chipSelected]}
                  >
                    <Text style={goalStatus === opt ? styles.chipTextSelected : styles.chipText}>
                      {opt}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>
          )}

          <Text style={styles.label}>Reflection (optional)</Text>
          <View style={styles.row}>
            {REFLECTION_CHIPS.map((chip) => (
              <TouchableOpacity
                key={chip}
                onPress={() => handleReflectionChip(chip)}
                style={styles.chip}
              >
                <Text style={styles.chipText}>+ {chip}</Text>
              </TouchableOpacity>
            ))}
          </View>
          <TextInput
            style={styles.input}
            value={reflectionText}
            onChangeText={setReflectionText}
            placeholder="Or write your own..."
            multiline
          />
        </>
      )}

      <Button
        title={submitting ? 'Submitting...' : 'Submit'}
        onPress={handleSubmit}
        disabled={submitting || mood === null}
      />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 20 },
  title: { fontSize: 20, fontWeight: '700', marginBottom: 16 },
  section: { marginBottom: 8 },
  label: { fontSize: 14, color: '#666', marginTop: 12, marginBottom: 4 },
  input: {
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 8,
    padding: 12,
    minHeight: 60,
    textAlignVertical: 'top',
    marginBottom: 12,
  },
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 8 },
  chip: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#ccc',
    backgroundColor: '#f5f5f5',
  },
  chipSelected: { backgroundColor: '#007bff', borderColor: '#007bff' },
  chipText: { color: '#333' },
  chipTextSelected: { color: '#fff' },
  courageBox: {
    backgroundColor: '#f0f4ff',
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
  },
  couragePrompt: { fontSize: 13, color: '#444', fontStyle: 'italic' },
});
