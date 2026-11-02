import { Image, Text, View } from 'react-native';
import Constants from 'expo-constants';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/AppNavigator';
import { useColors } from '../theme/colors';
import { useTheme } from '../contexts/ThemeContext';
import SettingsPage from '../components/settings/SettingsPage';

type Props = NativeStackScreenProps<RootStackParamList, 'About'>;

export default function AboutScreen({ navigation }: Props) {
  const colors = useColors();
  const { resolvedTheme } = useTheme();
  const version = Constants.expoConfig?.version ?? '1.0.0';
  return (
    <SettingsPage title="About" onBack={() => navigation.goBack()}>
      <View style={{ alignItems: 'center', marginTop: 40 }}>
        <Image
          source={
            resolvedTheme === 'dark'
              ? require('../assets/branding/04_mark_only_monochrome_dark.png')
              : require('../assets/branding/04_mark_only_monochrome_transparent.png')
          }
          resizeMode="contain"
          accessibilityLabel="Elvyn app icon"
          style={{ width: 112, height: 112, backgroundColor: colors.primarySoft, borderRadius: 28 }}
        />
        <Text style={{ color: colors.text, fontSize: 28, fontWeight: '800', marginTop: 16 }}>Elvyn</Text>
        <Text style={{ color: colors.textMuted, marginTop: 4 }}>Your Path to Elevation</Text>
        <Text style={{ color: colors.textMuted, marginTop: 20, fontSize: 13 }}>Version {version}</Text>
        <Text style={{ color: colors.textMuted, marginTop: 4, fontSize: 13 }}>Built by KunleTech · K.T Labs Ltd</Text>
      </View>
    </SettingsPage>
  );
}
