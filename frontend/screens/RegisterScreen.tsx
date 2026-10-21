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
import { friendlyAuthError, isValidEmail, MIN_PASSWORD } from '../utils/authErrors';


type Props = NativeStackScreenProps<RootStackParamList, 'Register'>;
type Errors = { name?: string; email?: string; password?: string; confirm?: string };

export default function RegisterScreen({ navigation }: Props) {
  const colors = useColors();
  const emailRef = useRef<TextInput>(null);
  const passRef = useRef<TextInput>(null);
  const confirmRef = useRef<TextInput>(null);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [errors, setErrors] = useState<Errors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);

  const clear = (key: keyof Errors) => setErrors((e) => ({ ...e, [key]: undefined }));

  function validate(): boolean {
    const next: Errors = {};
    if (!name.trim()) next.name = 'Enter your name.';
    if (!isValidEmail(email)) next.email = 'Enter a valid email address.';
    if (password.length < MIN_PASSWORD) next.password = `Use at least ${MIN_PASSWORD} characters.`;
    if (confirm !== password) next.confirm = "Passwords don't match.";
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function handleRegister() {
    setFormError(null);
    if (!validate()) return;
    setLoading(true);
    try {
      const fullName = name.trim();
      const { data, error } = await supabase.auth.signUp({
        email: email.trim(),
        password,
        options: { data: { full_name: fullName, first_name: fullName.split(/\s+/)[0] } },
      });
      if (error) { setFormError(friendlyAuthError(error)); return; }

      // Supabase returns a fake user with no identities when the email already exists
      if (data.user && data.user.identities?.length === 0) {
        setFormError('An account with this email already exists. Try logging in.');
        return;
      }
      if (data.session) {
        navigation.replace('MainTabs');;
      } else {
        Alert.alert('Check your email', 'We sent you a confirmation link. Confirm it, then log in.');
        navigation.navigate('Login');
      }
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
      if (session) navigation.replace('MainTabs');;
    } catch (err) {
      Alert.alert('Google sign-in', friendlyAuthError(err));
    } finally {
      setGoogleLoading(false);
    }
  }

  const busy = loading || googleLoading;

  return (
    <AuthScreen onBack={() => (navigation.canGoBack() ? navigation.goBack() : navigation.navigate('Login'))}>
      <AuthLogo />
      <Text style={{ color: colors.text, fontSize: 26, fontWeight: '800' }}>Create your account</Text>
      <Text style={{ color: colors.textMuted, marginTop: 6, marginBottom: 24 }}>
        Get started with ELVYN and take the first step towards a more focused, balanced you.
      </Text>

      <AuthInput
        icon="person-outline" placeholder="Full name" value={name}
        onChangeText={(v) => { setName(v); clear('name'); }} error={errors.name}
        autoCapitalize="words" autoComplete="name" textContentType="name"
        returnKeyType="next" onSubmitEditing={() => emailRef.current?.focus()}
      />
      <AuthInput
        ref={emailRef} icon="mail-outline" placeholder="Email address" value={email}
        onChangeText={(v) => { setEmail(v); clear('email'); }} error={errors.email}
        autoCapitalize="none" autoCorrect={false} keyboardType="email-address"
        autoComplete="email" textContentType="emailAddress"
        returnKeyType="next" onSubmitEditing={() => passRef.current?.focus()}
      />
      <AuthInput
        ref={passRef} icon="lock-closed-outline" placeholder="Password" secure value={password}
        onChangeText={(v) => { setPassword(v); clear('password'); }} error={errors.password}
        autoCapitalize="none" autoComplete="new-password" textContentType="newPassword"
        returnKeyType="next" onSubmitEditing={() => confirmRef.current?.focus()}
      />
      <AuthInput
        ref={confirmRef} icon="lock-closed-outline" placeholder="Confirm password" secure value={confirm}
        onChangeText={(v) => { setConfirm(v); clear('confirm'); }} error={errors.confirm}
        autoCapitalize="none" autoComplete="new-password" textContentType="newPassword"
        returnKeyType="done" onSubmitEditing={handleRegister}
      />

      {formError ? (
        <Text accessibilityRole="alert" style={{ color: colors.danger, marginVertical: 8, textAlign: 'center' }}>
          {formError}
        </Text>
      ) : null}

      <View style={{ marginTop: 8 }}>
        <PrimaryButton label="Create account" onPress={handleRegister} loading={loading} disabled={busy} />
      </View>

      <AuthDivider />

      <SecondaryButton
        label="Continue with Google" onPress={handleGoogle} loading={googleLoading} disabled={busy}
        leading={<Ionicons name="logo-google" size={20} color={colors.text} />}
      />

      <View style={{ flexDirection: 'row', justifyContent: 'center', marginTop: 28 }}>
        <Text style={{ color: colors.textMuted }}>Already have an account? </Text>
        <TouchableOpacity onPress={() => navigation.navigate('Login')}>
          <Text style={{ color: colors.primary, fontWeight: '700' }}>Log in</Text>
        </TouchableOpacity>
      </View>
    </AuthScreen>
  );
}