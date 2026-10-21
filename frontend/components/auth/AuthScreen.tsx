import type { ReactNode } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, TouchableOpacity, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useColors } from '../../theme/colors';

export default function AuthScreen({ children, onBack }: { children: ReactNode; onBack?: () => void }) {
  const colors = useColors();
  // Android already resizes via adjustResize (set in your manifest plugin), so a
  // KeyboardAvoidingView there would double-adjust. iOS needs it.
  const Wrapper: any = Platform.OS === 'ios' ? KeyboardAvoidingView : View;
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.background }}>
      <Wrapper style={{ flex: 1 }} {...(Platform.OS === 'ios' ? { behavior: 'padding' } : {})}>
        <ScrollView
          keyboardShouldPersistTaps="handled"
          contentContainerStyle={{ flexGrow: 1, padding: 24, paddingBottom: 32 }}
        >
          {onBack && (
            <TouchableOpacity onPress={onBack} hitSlop={12} accessibilityRole="button" accessibilityLabel="Back">
              <Ionicons name="arrow-back" size={24} color={colors.text} />
            </TouchableOpacity>
          )}
          {children}
        </ScrollView>
      </Wrapper>
    </SafeAreaView>
  );
}