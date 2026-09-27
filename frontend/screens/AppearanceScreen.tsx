import { ScrollView, Text, TouchableOpacity, View } from 'react-native';
import { useTheme, type ThemeMode } from '../contexts/ThemeContext';
import { useColors } from '../theme/colors';

const OPTIONS: { value: ThemeMode; label: string; description: string }[] = [
  { value: 'system', label: 'System', description: "Match your device's setting" },
  { value: 'light', label: 'Light', description: 'Always use light mode' },
  { value: 'dark', label: 'Dark', description: 'Always use dark mode' },
];

export default function AppearanceScreen({ navigation }: any) {
  const { mode, setMode } = useTheme();
  const colors = useColors();

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.background }}
      contentContainerStyle={{ padding: 20, paddingTop: 50 }}
    >
      <TouchableOpacity onPress={() => navigation.goBack()} accessibilityRole="button">
        <Text style={{ color: colors.text }}>← Back</Text>
      </TouchableOpacity>

      <Text style={{ fontSize: 20, fontWeight: '700', color: colors.text, marginTop: 16, marginBottom: 20 }}>
        Appearance
      </Text>

      {OPTIONS.map((option) => {
        const selected = mode === option.value;
        return (
          <TouchableOpacity
            key={option.value}
            onPress={() => setMode(option.value)}
            accessibilityRole="radio"
            accessibilityState={{ selected }}
            style={{
              flexDirection: 'row',
              alignItems: 'center',
              backgroundColor: colors.surface,
              borderRadius: 12,
              padding: 16,
              marginBottom: 10,
              borderWidth: 1,
              borderColor: selected ? colors.primary : colors.border,
            }}
          >
            <View
              style={{
                width: 20,
                height: 20,
                borderRadius: 10,
                borderWidth: 2,
                borderColor: selected ? colors.primary : colors.border,
                alignItems: 'center',
                justifyContent: 'center',
                marginRight: 14,
              }}
            >
              {selected && <View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: colors.primary }} />}
            </View>
            <View>
              <Text style={{ color: colors.text, fontWeight: '600' }}>{option.label}</Text>
              <Text style={{ color: colors.textMuted, fontSize: 12 }}>{option.description}</Text>
            </View>
          </TouchableOpacity>
        );
      })}
    </ScrollView>
  );
}
