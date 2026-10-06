import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';

//An array of mood objects, each containing a value and an emoji representation. The values range from 1 to 5, representing different moods from sad to happy.
const MOODS = [
  { value: 1, emoji: '😞' },
  { value: 2, emoji: '😕' },
  { value: 3, emoji: '😐' },
  { value: 4, emoji: '🙂' },
  { value: 5, emoji: '😄' },
];

type Props = {
  selected: number | null;
  onSelect: (value: number) => void;
};

export default function MoodPicker({ selected, onSelect }: Props) {
  return (
    <View style={styles.row}>
      {MOODS.map((m) => (
        <TouchableOpacity
          key={m.value}
          onPress={() => onSelect(m.value)}
          style={[styles.moodButton, selected === m.value && styles.selected]}
        >
          <Text style={styles.emoji}>{m.emoji}</Text>
        </TouchableOpacity>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', justifyContent: 'space-between', marginVertical: 16 },
  moodButton: {
    padding: 12,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: 'transparent',
  },
  selected: { borderColor: '#333', backgroundColor: '#eee' },
  emoji: { fontSize: 28 },
});
