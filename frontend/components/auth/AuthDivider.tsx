import { Text, View } from 'react-native';
import { useColors } from '../../theme/colors';

export default function AuthDivider() {
  const colors = useColors();
  const line = { flex: 1, height: 1, backgroundColor: colors.border };
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', marginVertical: 20 }}>
      <View style={line} />
      <Text style={{ color: colors.textMuted, marginHorizontal: 12, fontSize: 12 }}>OR</Text>
      <View style={line} />
    </View>
  );
}