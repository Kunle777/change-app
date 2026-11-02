import { Image, Platform, View } from 'react-native';
import { useTheme } from '../../contexts/ThemeContext';

export default function AuthLogo() {
  const isWeb = Platform.OS === 'web';
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';
  return (
    <View style={{ alignItems: 'center', marginTop: 8, marginBottom: 28 }}>
      <Image
        source={
          isWeb
            ? isDark
              ? require('../../assets/branding/05_horizontal_logo_lockup_dark.png')
              : require('../../assets/branding/05_horizontal_logo_lockup_transparent.png')
            : isDark
              ? require('../../assets/branding/01_primary_stacked_logo_dark.png')
              : require('../../assets/branding/01_primary_stacked_logo_transparent.png')
        }
        resizeMode="contain"
        accessibilityLabel="Elvyn — Your Path to Elevation"
        style={{ width: isWeb ? 260 : 230, height: isWeb ? 110 : 180 }}
      />
    </View>
  );
}