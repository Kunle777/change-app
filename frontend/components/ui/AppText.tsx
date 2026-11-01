import { Text } from 'react-native';
import type { TextProps } from 'react-native';
import { maxFontSizeMultiplier, typography } from '../../theme/typography';
import type { TypographyVariant } from '../../theme/typography';

interface AppTextProps extends TextProps {
  variant: TypographyVariant;
}

export default function AppText({ variant, style, ...props }: AppTextProps) {
  return (
    <Text
      {...props}
      allowFontScaling
      maxFontSizeMultiplier={maxFontSizeMultiplier[variant]}
      style={[typography[variant], style]}
    />
  );
}
