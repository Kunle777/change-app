import React, { useEffect, useState } from 'react';
import { View, Text, TextInput, Button, StyleSheet, Alert, TouchableOpacity, ScrollView } from 'react-native';
import MoodPicker from '../components/MoodPicker';
import { submitMorningCheckin, submitEveningCheckin, getTodayCheckinStatus } from '../services/checkins';
import { API_BASE_URL } from '../services/api';
import { supabase } from '../services/supabase';

const REFLECTION_CHIPS = ['Got a lot done', 'Slower day', 'Tired', 'Proud of today', 'Struggled'];

type Props = {
  route: { params: { type: 'morning' | 'evening' } };
  navigation: any;
};

export default function CheckInScreen({ route, navigation }: Props) {
  const { type } = route.params;
  const [mood, setMood] = useState<number | null>(null);
  const [text, setText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [morningGoal, setMorningGoal] = useState<string | null>(null);

  useEffect(() => {
    if (type === 'evening') fetchMorningGoal();
  }, []);

  async function fetchMorningGoal() {
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      const res = await fetch(`${API_BASE_URL}/api/checkins/history?limit=5`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) return;
      const history: { type: string; goal_today?: string; created_at: string }[] = await res.json();
      const todayStr = new Date().toISOString().slice(0, 10);
      const morningEntry = history.find(
        (c) => c.type === 'morning' && c.created_at.startsWith(todayStr) && c.goal_today
      );
      if (morningEntry?.goal_today) setMorningGoal(morningEntry.goal_today);
    } catch {}
  }

  const handleSubmit = async () => {
    if (mood === null) {
      Alert.alert('Pick a mood first');
      return;
    }
    setSubmitting(true);
    try {
      if (type === 'morning') {
        await submitMorningCheckin(mood, text);
      } else {
        await submitEveningCheckin(mood, text);
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
          <TextInput
            style={styles.input}
            value={text}
            onChangeText={setText}
            placeholder="e.g. Finish the AI wrapper"
            multiline
          />
        </>
      )}

      {type === 'evening' && (
        <>
          {morningGoal && (
            <>
              <Text style={styles.label}>Did you get to: "{morningGoal}"?</Text>
              <View style={styles.row}>
                {['Yes', 'Partially', 'No'].map((opt) => (
                  <TouchableOpacity
                    key={opt}
                    onPress={() => setText(opt)}
                    style={[styles.chip, text === opt && styles.chipSelected]}
                  >
                    <Text style={text === opt && styles.chipTextSelected}>{opt}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            </>
          )}

          <Text style={styles.label}>Reflection (optional)</Text>
          <View style={styles.row}>
            {REFLECTION_CHIPS.map((c) => (
              <TouchableOpacity
                key={c}
                onPress={() => setText(c)}
                style={[styles.chip, text === c && styles.chipSelected]}
              >
                <Text style={text === c && styles.chipTextSelected}>{c}</Text>
              </TouchableOpacity>
            ))}
          </View>
          <TextInput
            style={styles.input}
            value={text}
            onChangeText={setText}
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
  chipTextSelected: { color: '#fff' },
});
