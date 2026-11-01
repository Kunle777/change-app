import { Text, View } from 'react-native';
import Constants from 'expo-constants';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/AppNavigator';
import { useColors } from '../theme/colors';
import ElvynMascot from '../components/ElvynMascot';
import SettingsPage from '../components/settings/SettingsPage';

type Props = NativeStackScreenProps<RootStackParamList, 'About'>;

export default function AboutScreen({ navigation }: Props) {
  const colors = useColors();
  const version = Constants.expoConfig?.version ?? '1.0.0';
  return (
    <SettingsPage title="About" onBack={() => navigation.goBack()}>
      <View style={{ alignItems: 'center', marginTop: 40 }}>
        <ElvynMascot variant="neutral" size={96} />
        <Text style={{ color: colors.text, fontSize: 28, fontWeight: '800', marginTop: 16 }}>Elvyn</Text>
        <Text style={{ color: colors.textMuted, marginTop: 4 }}>Make Progress Personal.</Text>
        <Text style={{ color: colors.textMuted, marginTop: 20, fontSize: 13 }}>Version {version}</Text>
        <Text style={{ color: colors.textMuted, marginTop: 4, fontSize: 13 }}>Built by KunleTech · K.T Labs Ltd</Text>
      </View>
    </SettingsPage>
  );
}
