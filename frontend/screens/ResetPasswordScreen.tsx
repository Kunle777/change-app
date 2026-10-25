import { useEffect, useRef, useState } from 'react';
import { Text, TextInput, TouchableOpacity, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { supabase } from '../services/supabase';
import { RootStackParamList } from '../navigation/AppNavigator';
import { useColors } from '../theme/colors';
import AuthScreen from '../components/auth/AuthScreen';
import AuthInput from '../components/auth/AuthInput';
import { PrimaryButton } from '../components/auth/Buttons';
import { friendlyAuthError, MIN_PASSWORD } from '../utils/authErrors';

type Props = NativeStackScreenProps<RootStackParamList, 'ResetPassword'>;

export default function ResetPasswordScreen({ navigation, route }: Props) {
  const colors = useColors();
  const confirmRef = useRef<TextInput>(null);
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  // 'checking' until we know the recovery session from the link really exists.
  const [linkState, setLinkState] = useState<'checking' | 'ok' | 'bad'>(route.params?.error ? 'bad' : 'checking');

  useEffect(() => {
    if (route.params?.error) return;
    supabase.auth.getSession().then(({ data }) => setLinkState(data.session ? 'ok' : 'bad'));
  }, [route.params?.error]);

  function goToLogin() {
    navigation.reset({ index: 0, routes: [{ name: 'Login' }] });
  }

  async function handleSave() {
    setFormError(null);
    const pErr = password.length >= MIN_PASSWORD ? null : `Use at least ${MIN_PASSWORD} characters.`;
    const cErr = confirm === password ? null : "The two passwords don't match.";
    setPasswordError(pErr);
    setConfirmError(cErr);
    if (pErr || cErr) return;

    setLoading(true);
    try {
      const { error } = await supabase.auth.updateUser({ password });
      if (error) { setFormError(friendlyAuthError(error)); return; }
      // The link signed this phone in; end that session so the person logs in
      // with the new password and we know it works.
      await supabase.auth.signOut();
      setDone(true);
    } catch (err) {
      setFormError(friendlyAuthError(err));
    } finally {
      setLoading(false);
    }
  }

  if (linkState === 'checking') return <AuthScreen><View /></AuthScreen>;

  if (linkState === 'bad') {
    return (
      <AuthScreen>
        <View style={{ alignItems: 'center', marginTop: 48 }}>
          <Ionicons name="time-outline" size={56} color={colors.primary} />
          <Text style={{ color: colors.text, fontSize: 24, fontWeight: '800', marginTop: 20 }}>
            That link didn't work
          </Text>
          <Text style={{ color: colors.textMuted, marginTop: 8, textAlign: 'center', lineHeight: 21 }}>
            {route.params?.error ?? 'It may have expired or already been used. Request a new one and open it on this phone.'}
          </Text>
        </View>
        <View style={{ marginTop: 32 }}>
          <PrimaryButton
            label="Request a new link"
            onPress={() => navigation.reset({ index: 1, routes: [{ name: 'Login' }, { name: 'ForgotPassword' }] })}
          />
          <TouchableOpacity onPress={goToLogin} style={{ alignSelf: 'center', marginTop: 24 }} hitSlop={8}>
            <Text style={{ color: colors.primary, fontWeight: '700' }}>Back to log in</Text>
          </TouchableOpacity>
        </View>
      </AuthScreen>
    );
  }

  if (done) {
    return (
      <AuthScreen>
        <View style={{ alignItems: 'center', marginTop: 48 }}>
          <Ionicons name="checkmark-circle-outline" size={64} color={colors.primary} />
          <Text style={{ color: colors.text, fontSize: 24, fontWeight: '800', marginTop: 20 }}>
            Password updated
          </Text>
          <Text style={{ color: colors.textMuted, marginTop: 8, textAlign: 'center' }}>
            Log in with your new password to continue.
          </Text>
        </View>
        <View style={{ marginTop: 32 }}>
          <PrimaryButton label="Go to log in" onPress={goToLogin} />
        </View>
      </AuthScreen>
    );
  }

  return (
    <AuthScreen>
      <Text style={{ color: colors.text, fontSize: 26, fontWeight: '800', marginTop: 24 }}>
        Set a new password
      </Text>
      <Text style={{ color: colors.textMuted, marginTop: 6, marginBottom: 24 }}>
        Choose something you'll remember, at least {MIN_PASSWORD} characters.
      </Text>

      <AuthInput
        icon="lock-closed-outline"
        placeholder="New password"
        secure
        value={password}
        onChangeText={(v) => { setPassword(v); setPasswordError(null); }}
        error={passwordError}
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
        onSubmitEditing={handleSave}
      />

      {formError ? (
        <Text accessibilityRole="alert" style={{ color: colors.danger, marginBottom: 12, textAlign: 'center' }}>
          {formError}
        </Text>
      ) : null}

      <View style={{ marginTop: 8 }}>
        <PrimaryButton label="Save new password" onPress={handleSave} loading={loading} />
      </View>
    </AuthScreen>
  );
}
