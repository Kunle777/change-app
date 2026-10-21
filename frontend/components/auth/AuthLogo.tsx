import { Text, View } from 'react-native';
import { useColors } from '../../theme/colors';

export default function AuthLogo() {
  const colors = useColors();
  return (
    <View style={{ alignItems: 'center', marginTop: 8, marginBottom: 28 }}>
      {/* TODO: swap for your lockup SVG, e.g. <ElvynLockup width={180} height={140} /> */}
      <Text style={{ color: colors.text, fontSize: 30, fontWeight: '800', letterSpacing: 8 }}>ELVYN</Text>
      <Text style={{ color: colors.textMuted, fontSize: 14, marginTop: 6 }}>Make Progress Personal.</Text>
    </View>
  );
}