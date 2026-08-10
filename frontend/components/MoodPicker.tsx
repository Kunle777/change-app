import React from 'react';
import { View, TouchableOpacity, Text, StyleSheet } from 'react-native';

const MOODS = ['😞', '😕', '😐', '🙂', '😄'];

type Props = {
  selected: number | null;
  onSelect: (mood: number) => void;
};

export default function MoodPicker({ selected, onSelect }: Props) {
  return (
    <View style={styles.row}>
      {MOODS.map((emoji, index) => {
        const value = index + 1;
        return (
          <TouchableOpacity
            key={value}
            onPress={() => onSelect(value)}
            style={[styles.item, selected === value && styles.selected]}
          >
            <Text style={styles.emoji}>{emoji}</Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', justifyContent: 'space-between', marginVertical: 8 },
  item: {
    padding: 8,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: 'transparent',
  },
  selected: { borderColor: '#007bff', backgroundColor: '#e8f0fe' },
  emoji: { fontSize: 28 },
});
