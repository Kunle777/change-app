import { useRef, useState } from 'react';
import { Alert, Text, TextInput, TouchableOpacity, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { supabase } from '../services/supabase';
import { signInWithGoogle } from '../services/google_auth';
import { RootStackParamList } from '../navigation/AppNavigator';
import { useColors } from '../theme/colors';
import AuthScreen from '../components/auth/AuthScreen';
import AuthLogo from '../components/auth/AuthLogo';
import AuthInput from '../components/auth/AuthInput';
import AuthDivider from '../components/auth/AuthDivider';
import { PrimaryButton, SecondaryButton } from '../components/auth/Buttons';
import { friendlyAuthError, isValidEmail } from '../utils/authErrors';


type Props = NativeStackScreenProps<RootStackParamList, 'Login'>;

export default function LoginScreen({ navigation }: Props) {
  const colors = useColors();
  const passwordRef = useRef<TextInput>(null);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [emailError, setEmailError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);

  async function goNext() {
    navigation.replace('MainTabs');;
  }

  async function handleLogin() {
    setFormError(null);
    const eErr = isValidEmail(email) ? null : 'Enter a valid email address.';
    const pErr = password ? null : 'Enter your password.';
    setEmailError(eErr);
    setPasswordError(pErr);
    if (eErr || pErr) return;

    setLoading(true);
    try {
      const { error } = await supabase.auth.signInWithPassword({ email: email.trim(), password });
      if (error) { setFormError(friendlyAuthError(error)); return; }
      await goNext();
    } catch (err) {
      setFormError(friendlyAuthError(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleGoogle() {
    setFormError(null);
    setGoogleLoading(true);
    try {
      const session = await signInWithGoogle();
      if (session) await goNext(); // null = user backed out, stay silent
    } catch (err) {
      Alert.alert('Google sign-in', friendlyAuthError(err));
    } finally {
      setGoogleLoading(false);
    }
  }

  const busy = loading || googleLoading;

  return (
    <AuthScreen>
      <AuthLogo />
      <Text style={{ color: colors.text, fontSize: 26, fontWeight: '800' }}>Welcome back 👋</Text>
      <Text style={{ color: colors.textMuted, marginTop: 6, marginBottom: 24 }}>
        Log in to continue your journey.
      </Text>

      <AuthInput
        icon="mail-outline"
        placeholder="Email address"
        value={email}
        onChangeText={(v) => { setEmail(v); setEmailError(null); }}
        error={emailError}
        autoCapitalize="none"
        autoCorrect={false}
        keyboardType="email-address"
        autoComplete="email"
        textContentType="emailAddress"
        returnKeyType="next"
        onSubmitEditing={() => passwordRef.current?.focus()}
      />
      <AuthInput
        ref={passwordRef}
        icon="lock-closed-outline"
        placeholder="Password"
        secure
        value={password}
        onChangeText={(v) => { setPassword(v); setPasswordError(null); }}
        error={passwordError}
        autoCapitalize="none"
        autoComplete="current-password"
        textContentType="password"
        returnKeyType="done"
        onSubmitEditing={handleLogin}
      />

      <TouchableOpacity
        onPress={() => navigation.navigate('ForgotPassword')}
        style={{ alignSelf: 'flex-end', marginBottom: 20 }}
        hitSlop={8}
      >
        <Text style={{ color: colors.primary, fontWeight: '600', fontSize: 13 }}>Forgot password?</Text>
      </TouchableOpacity>

      {formError ? (
        <Text accessibilityRole="alert" style={{ color: colors.danger, marginBottom: 12, textAlign: 'center' }}>
          {formError}
        </Text>
      ) : null}

      <PrimaryButton label="Log in" onPress={handleLogin} loading={loading} disabled={busy} />

      <AuthDivider />

      <SecondaryButton
        label="Continue with Google"
        onPress={handleGoogle}
        loading={googleLoading}
        disabled={busy}
        leading={<Ionicons name="logo-google" size={20} color={colors.text} />}
      />

      <View style={{ flexDirection: 'row', justifyContent: 'center', marginTop: 28 }}>
        <Text style={{ color: colors.textMuted }}>Don't have an account? </Text>
        <TouchableOpacity onPress={() => navigation.navigate('Register')}>
          <Text style={{ color: colors.primary, fontWeight: '700' }}>Sign up</Text>
        </TouchableOpacity>
      </View>
    </AuthScreen>
  );
}