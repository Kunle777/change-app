import { forwardRef, useState } from 'react';
import { Text, TextInput, TextInputProps, TouchableOpacity, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useColors } from '../../theme/colors';

type Props = TextInputProps & {
  icon: keyof typeof Ionicons.glyphMap;
  error?: string | null;
  secure?: boolean;
};

const AuthInput = forwardRef<TextInput, Props>(
  ({ icon, error, secure, onFocus, onBlur, ...rest }, ref) => {
    const colors = useColors();
    const [focused, setFocused] = useState(false);
    const [hidden, setHidden] = useState(true);

    return (
      <View style={{ marginBottom: 12 }}>
        <View
          style={{
            flexDirection: 'row',
            alignItems: 'center',
            backgroundColor: colors.surface,
            borderWidth: 1,
            borderColor: error ? colors.danger : focused ? colors.primary : colors.border,
            borderRadius: 14,
            paddingHorizontal: 14,
            minHeight: 54,
          }}
        >
          <Ionicons name={icon} size={20} color={colors.textMuted} />
          <TextInput
            ref={ref}
            {...rest}
            secureTextEntry={secure ? hidden : false}
            placeholderTextColor={colors.textMuted}
            onFocus={(e) => { setFocused(true); onFocus?.(e); }}
            onBlur={(e) => { setFocused(false); onBlur?.(e); }}
            style={{ flex: 1, marginLeft: 12, fontSize: 15, color: colors.text, paddingVertical: 12 }}
          />
          {secure && (
            <TouchableOpacity
              onPress={() => setHidden((h) => !h)}
              hitSlop={10}
              accessibilityRole="button"
              accessibilityLabel={hidden ? 'Show password' : 'Hide password'}
            >
              <Ionicons name={hidden ? 'eye-outline' : 'eye-off-outline'} size={20} color={colors.textMuted} />
            </TouchableOpacity>
          )}
        </View>
        {error ? (
          <Text accessibilityRole="alert" style={{ color: colors.danger, fontSize: 12, marginTop: 4, marginLeft: 4 }}>
            {error}
          </Text>
        ) : null}
      </View>
    );
  },
);
export default AuthInput;