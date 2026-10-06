import { View, TouchableOpacity, Text } from 'react-native';

const CHIPS = [
  "How's my week looking?",
  'What should I focus on?',
  "I'm stuck on a task",
  'Why do I keep postponing things?',
];

export default function AIPromptChips({ onSelect }: { onSelect: (text: string) => void }) {
  return (
    <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
      {CHIPS.map((chip) => (
        <TouchableOpacity
          key={chip}
          onPress={() => onSelect(chip)}
          style={{
            borderWidth: 1,
            borderColor: '#ddd',
            borderRadius: 12,
            paddingVertical: 10,
            paddingHorizontal: 14,
            width: '47%',
          }}
        >
          <Text style={{ fontSize: 13 }}>✦ {chip}</Text>
        </TouchableOpacity>
      ))}
    </View>
  );
}
