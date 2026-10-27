import { Text, TouchableOpacity, View } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useTheme, type ThemeMode } from '../contexts/ThemeContext';
import { RootStackParamList } from '../navigation/AppNavigator';
import { useColors } from '../theme/colors';
import SettingsPage from '../components/settings/SettingsPage';

type Props = NativeStackScreenProps<RootStackParamList, 'Appearance'>;

const OPTIONS: { value: ThemeMode; label: string; description: string }[] = [
  { value: 'system', label: 'System (recommended)', description: 'Follows your device settings' },
  { value: 'light', label: 'Light', description: 'Bright and clean' },
  { value: 'dark', label: 'Dark', description: 'Easy on your eyes' },
];

export default function AppearanceScreen({ navigation }: Props) {
  const { mode, setMode } = useTheme();
  const colors = useColors();

  return (
    <SettingsPage title="Appearance" onBack={() => navigation.goBack()}>
      <Text style={{ color: colors.textMuted, fontSize: 12, fontWeight: '700', letterSpacing: 0.8, marginTop: 22, marginBottom: 8, marginLeft: 4 }}>
        THEME
      </Text>
      {OPTIONS.map((option) => {
        const selected = mode === option.value;
        return (
          <TouchableOpacity
            key={option.value}
            onPress={() => setMode(option.value)}
            accessibilityRole="radio"
            accessibilityState={{ selected }}
            activeOpacity={0.8}
            style={{
              flexDirection: 'row', alignItems: 'center', backgroundColor: colors.surface, borderRadius: 16,
              padding: 16, marginBottom: 10, borderWidth: selected ? 2 : 1,
              borderColor: selected ? colors.primary : colors.border,
            }}
          >
            <View
              style={{
                width: 22, height: 22, borderRadius: 11, borderWidth: 2, marginRight: 14,
                borderColor: selected ? colors.primary : colors.border, alignItems: 'center', justifyContent: 'center',
              }}
            >
              {selected ? <View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: colors.primary }} /> : null}
            </View>
            <View>
              <Text style={{ color: colors.text, fontWeight: '600', fontSize: 15 }}>{option.label}</Text>
              <Text style={{ color: colors.textMuted, fontSize: 12.5, marginTop: 2 }}>{option.description}</Text>
            </View>
          </TouchableOpacity>
        );
      })}
    </SettingsPage>
  );
}
