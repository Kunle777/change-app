import { useState } from 'react';
import { Text, TextInput, View } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { clearPasscode, setPasscode, verifyPasscode } from '../services/passcode';
import { RootStackParamList } from '../navigation/AppNavigator';
import { useColors } from '../theme/colors';
import AuthScreen from '../components/auth/AuthScreen';
import { PrimaryButton } from '../components/auth/Buttons';

type Props = NativeStackScreenProps<RootStackParamList, 'PasscodeSetup'>;
type Stage = 'current' | 'enter' | 'confirm';

const TITLES: Record<Stage, string> = {
  current: 'Enter your current passcode',
  enter: 'Choose a passcode',
  confirm: 'Confirm your passcode',
};
const HINTS: Record<Stage, string> = {
  current: 'We need to check it is you.',
  enter: 'Use 4 to 6 digits.',
  confirm: 'Enter it once more.',
};

export default function PasscodeSetupScreen({ navigation, route }: Props) {
  const colors = useColors();
  const mode = route.params?.mode ?? 'create';
  const [stage, setStage] = useState<Stage>(mode === 'create' ? 'enter' : 'current');
  const [first, setFirst] = useState('');
  const [value, setValue] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleContinue() {
    setError(null);
    if (value.length < 4) {
      setError('Use at least 4 digits.');
      return;
    }
    setBusy(true);
    try {
      if (stage === 'current') {
        if (!(await verifyPasscode(value))) {
          setError('That passcode is not correct.');
          setValue('');
          return;
        }
        if (mode === 'disable') {
          await clearPasscode();
          navigation.goBack();
          return;
        }
        setStage('enter');
        setValue('');
        return;
      }
      if (stage === 'enter') {
        setFirst(value);
        setStage('confirm');
        setValue('');
        return;
      }
      if (value !== first) {
        setError("Those don't match. Try again.");
        setStage('enter');
        setFirst('');
        setValue('');
        return;
      }
      await setPasscode(value);
      navigation.goBack();
    } catch {
      setError('Something went wrong. Please try again.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthScreen onBack={() => navigation.goBack()}>
      <Text style={{ color: colors.text, fontSize: 26, fontWeight: '800', marginTop: 24 }}>{TITLES[stage]}</Text>
      <Text style={{ color: colors.textMuted, marginTop: 6, marginBottom: 28 }}>{HINTS[stage]}</Text>

      <View
        style={{
          backgroundColor: colors.surface, borderRadius: 14, borderWidth: 1,
          borderColor: error ? colors.danger : colors.border, marginBottom: 8,
        }}
      >
        <TextInput
          key={stage}
          value={value}
          onChangeText={(v) => { setValue(v.replace(/\D/g, '')); setError(null); }}
          keyboardType="number-pad"
          secureTextEntry
          maxLength={6}
          autoFocus
          accessibilityLabel={TITLES[stage]}
          onSubmitEditing={handleContinue}
          style={{ color: colors.text, fontSize: 28, letterSpacing: 12, textAlign: 'center', paddingVertical: 16 }}
        />
      </View>
      {error ? (
        <Text accessibilityRole="alert" style={{ color: colors.danger, textAlign: 'center', marginBottom: 8 }}>
          {error}
        </Text>
      ) : null}

      <View style={{ marginTop: 16 }}>
        <PrimaryButton
          label={mode === 'disable' && stage === 'current' ? 'Turn off passcode' : 'Continue'}
          onPress={handleContinue}
          loading={busy}
        />
      </View>
    </AuthScreen>
  );
}
