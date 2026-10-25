import { useEffect, useRef, useState } from 'react';
import { Text, TextInput, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { supabase } from '../services/supabase';
import { RootStackParamList } from '../navigation/AppNavigator';
import { useColors } from '../theme/colors';
import AuthScreen from '../components/auth/AuthScreen';
import AuthInput from '../components/auth/AuthInput';
import { PrimaryButton } from '../components/auth/Buttons';
import { friendlyAuthError, MIN_PASSWORD } from '../utils/authErrors';

type Props = NativeStackScreenProps<RootStackParamList, 'ChangePassword'>;

export default function ChangePasswordScreen({ navigation }: Props) {
  const colors = useColors();
  const newRef = useRef<TextInput>(null);
  const confirmRef = useRef<TextInput>(null);
  const [email, setEmail] = useState<string | null>(null);
  // Google-only accounts have no password yet, so there is nothing to confirm.
  const [hasPassword, setHasPassword] = useState(true);
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [currentError, setCurrentError] = useState<string | null>(null);
  const [nextError, setNextError] = useState<string | null>(null);
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      const user = data.user;
      setEmail(user?.email ?? null);
      const providers: string[] = user?.app_metadata?.providers ?? [];
      setHasPassword(providers.length === 0 || providers.includes('email'));
    });
  }, []);

  async function handleChange() {
    setFormError(null);
    const needCurrent = hasPassword && !!email;
    const cErr = needCurrent && !current ? 'Enter your current password.' : null;
    const nErr = next.length < MIN_PASSWORD ? `Use at least ${MIN_PASSWORD} characters.` : null;
    const mErr = confirm === next ? null : "The two passwords don't match.";
    setCurrentError(cErr);
    setNextError(nErr);
    setConfirmError(mErr);
    if (cErr || nErr || mErr) return;

    setLoading(true);
    try {
      if (needCurrent) {
        // Re-checks the current password so a borrowed, unlocked phone can't
        // be used to take over the account.
        const { error: verifyError } = await supabase.auth.signInWithPassword({ email: email!, password: current });
        if (verifyError) {
          if (verifyError.code === 'invalid_credentials') setCurrentError('That password is not correct.');
          else setFormError(friendlyAuthError(verifyError));
          return;
        }
      }
      const { error } = await supabase.auth.updateUser({ password: next });
      if (error) { setFormError(friendlyAuthError(error)); return; }
      setDone(true);
    } catch (err) {
      setFormError(friendlyAuthError(err));
    } finally {
      setLoading(false);
    }
  }

  if (done) {
    return (
      <AuthScreen>
        <View style={{ alignItems: 'center', marginTop: 64 }}>
          <Ionicons name="checkmark-circle-outline" size={64} color={colors.primary} />
          <Text style={{ color: colors.text, fontSize: 24, fontWeight: '800', marginTop: 20 }}>
            Password changed
          </Text>
          <Text style={{ color: colors.textMuted, marginTop: 8, textAlign: 'center' }}>
            Use your new password next time you log in.
          </Text>
        </View>
        <View style={{ marginTop: 32 }}>
          <PrimaryButton label="Done" onPress={() => navigation.goBack()} />
        </View>
      </AuthScreen>
    );
  }

  return (
    <AuthScreen onBack={() => navigation.goBack()}>
      <Text style={{ color: colors.text, fontSize: 26, fontWeight: '800', marginTop: 24 }}>
        Change password
      </Text>
      <Text style={{ color: colors.textMuted, marginTop: 6, marginBottom: 24 }}>
        {hasPassword
          ? `Confirm your current password, then choose a new one of at least ${MIN_PASSWORD} characters.`
          : `You signed in with Google. Set a password if you'd also like to log in with your email (at least ${MIN_PASSWORD} characters).`}
      </Text>

      {hasPassword && email ? (
        <AuthInput
          icon="key-outline"
          placeholder="Current password"
          secure
          value={current}
          onChangeText={(v) => { setCurrent(v); setCurrentError(null); }}
          error={currentError}
          autoCapitalize="none"
          autoComplete="current-password"
          textContentType="password"
          returnKeyType="next"
          onSubmitEditing={() => newRef.current?.focus()}
        />
      ) : null}
      <AuthInput
        ref={newRef}
        icon="lock-closed-outline"
        placeholder="New password"
        secure
        value={next}
        onChangeText={(v) => { setNext(v); setNextError(null); }}
        error={nextError}
        autoCapitalize="none"
        autoComplete="new-password"
        textContentType="newPassword"
        returnKeyType="next"
        onSubmitEditing={() => confirmRef.current?.focus()}
      />
      <AuthInput
        ref={confirmRef}
        icon="lock-closed-outline"
        placeholder="Confirm new password"
        secure
        value={confirm}
        onChangeText={(v) => { setConfirm(v); setConfirmError(null); }}
        error={confirmError}
        autoCapitalize="none"
        autoComplete="new-password"
        textContentType="newPassword"
        returnKeyType="done"
        onSubmitEditing={handleChange}
      />

      {formError ? (
        <Text accessibilityRole="alert" style={{ color: colors.danger, marginBottom: 12, textAlign: 'center' }}>
          {formError}
        </Text>
      ) : null}

      <View style={{ marginTop: 8 }}>
        <PrimaryButton label="Change password" onPress={handleChange} loading={loading} />
      </View>
    </AuthScreen>
  );
}
