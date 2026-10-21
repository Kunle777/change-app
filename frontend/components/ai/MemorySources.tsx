import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';

export type MemorySource = {
  id: string;
  source_type: string;
  kind: string;
  date: string;
  snippet: string;
};

export default function MemorySources({ sources }: { sources?: MemorySource[] }) {
  const [open, setOpen] = useState(false);
  if (!sources || sources.length === 0) return null;
  const n = sources.length;
  return (
    <View style={styles.wrap}>
      <TouchableOpacity onPress={() => setOpen(value => !value)} accessibilityRole="button">
        <Text style={styles.toggle}>Entries I looked at ({n}) {open ? '▾' : '▸'}</Text>
      </TouchableOpacity>
      {open && sources.map(source => (
        <View key={source.source_type + ':' + source.id} style={styles.item}>
          <Text style={styles.meta}>{source.kind} — {source.date}</Text>
          <Text style={styles.snippet}>{source.snippet}</Text>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { marginTop: 6 },
  toggle: { color: '#4F46E5', fontSize: 12, fontWeight: '600' },
  item: { marginTop: 6, paddingLeft: 8, borderLeftWidth: 2, borderLeftColor: '#C7D2FE' },
  meta: { color: '#6B7280', fontSize: 11 },
  snippet: { color: '#111827', fontSize: 12 },
});
