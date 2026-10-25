import React, { useState } from 'react';
import { View, Text, TouchableOpacity } from 'react-native';
import { useColors } from '../../theme/colors';

export type MemorySource = {
  id: string;
  source_type: string;
  kind: string;
  date: string;
  snippet: string;
};

export default function MemorySources({ sources }: { sources?: MemorySource[] }) {
  const colors = useColors();
  const [open, setOpen] = useState(false);
  if (!sources || sources.length === 0) return null;
  return (
    <View style={{ marginTop: 10 }}>
      <TouchableOpacity
        onPress={() => setOpen((value) => !value)}
        accessibilityRole="button"
        accessibilityLabel="Show the entries Elvyn looked at"
        style={{
          alignSelf: 'flex-start',
          backgroundColor: colors.primarySoft,
          borderRadius: 12,
          paddingHorizontal: 10,
          paddingVertical: 5,
        }}
      >
        <Text style={{ color: colors.primary, fontSize: 12, fontWeight: '600' }}>
          From your entries ({sources.length}) {open ? '▾' : '▸'}
        </Text>
      </TouchableOpacity>
      {open &&
        sources.map((source) => (
          <View
            key={`${source.source_type}:${source.id}`}
            style={{ marginTop: 8, paddingLeft: 10, borderLeftWidth: 2, borderLeftColor: colors.primary }}
          >
            <Text style={{ color: colors.textMuted, fontSize: 11 }}>
              {source.kind} · {source.date}
            </Text>
            <Text style={{ color: colors.text, fontSize: 12, marginTop: 2 }}>{source.snippet}</Text>
          </View>
        ))}
    </View>
  );
}
