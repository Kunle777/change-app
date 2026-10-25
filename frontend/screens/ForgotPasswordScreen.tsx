import { useEffect, useState } from 'react';
import { Text, TouchableOpacity, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { supabase } from '../services/supabase';
import { RootStackParamList } from '../navigation/AppNavigator';
import { useColors } from '../theme/colors';
import AuthScreen from '../components/auth/AuthScreen';
import AuthInput from '../components/auth/AuthInput';
import { PrimaryButton, SecondaryButton } from '../components/auth/Buttons';
import { friendlyAuthError, isValidEmail } from '../utils/authErrors';

type Props = NativeStackScreenProps<RootStackParamList, 'ForgotPassword'>;

const RESEND_SECONDS = 60;

export default function ForgotPasswordScreen({ navigation }: Props) {
  const colors = useColors();
  const [email, setEmail] = useState('');
  const [emailError, setEmailError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [cooldown, setCooldown] = useState(0);

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(timer);
  }, [cooldown]);

  async function handleSend() {
    setFormError(null);
    if (!isValidEmail(email)) {
      setEmailError('Enter a valid email address.');
      return;
    }
    setEmailError(null);

    setLoading(true);
    try {
      const { error } = await supabase.auth.resetPasswordForEmail(email.trim(), {
        redirectTo: 'elvyn://reset-password',
      });
      if (error) {
        setFormError(friendlyAuthError(error));
        return;
      }
      // Same message whether or not the account exists, so this screen can't be
      // used to find out who has an account.
      setSent(true);
      setCooldown(RESEND_SECONDS);
    } catch (err) {
      setFormError(friendlyAuthError(err));
    } finally {
      setLoading(false);
    }
  }

  if (sent) {
    return (
      <AuthScreen onBack={() => navigation.goBack()}>
        <View style={{ alignItems: 'center', marginTop: 40 }}>
          <View
            style={{
              width: 88, height: 88, borderRadius: 44, alignItems: 'center', justifyContent: 'center',
              backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border,
            }}
          >
            <Ionicons name="mail-open-outline" size={40} color={colors.primary} />
          </View>
          <Text style={{ color: colors.text, fontSize: 24, fontWeight: '800', marginTop: 24 }}>
            Check your email
          </Text>
          <Text style={{ color: colors.textMuted, marginTop: 8, textAlign: 'center', lineHeight: 21 }}>
            If an account exists for {email.trim()}, a reset link is on its way. Open it on this phone.
            It can take a minute, and it may land in spam.
          </Text>
        </View>

        <View style={{ marginTop: 32 }}>
          <SecondaryButton
            label={cooldown > 0 ? `Send again in ${cooldown}s` : 'Send again'}
            onPress={handleSend}
            loading={loading}
            disabled={cooldown > 0}
          />
          {formError ? (
            <Text accessibilityRole="alert" style={{ color: colors.danger, marginTop: 12, textAlign: 'center' }}>
              {formError}
            </Text>
          ) : null}
          <TouchableOpacity onPress={() => navigation.goBack()} style={{ alignSelf: 'center', marginTop: 24 }} hitSlop={8}>
            <Text style={{ color: colors.primary, fontWeight: '700' }}>Back to log in</Text>
          </TouchableOpacity>
        </View>
      </AuthScreen>
    );
  }

  return (
    <AuthScreen onBack={() => navigation.goBack()}>
      <Text style={{ color: colors.text, fontSize: 26, fontWeight: '800', marginTop: 24 }}>
        Forgot your password?
      </Text>
      <Text style={{ color: colors.textMuted, marginTop: 6, marginBottom: 24, lineHeight: 21 }}>
        No worries. Enter your email and we'll send you a link to set a new one.
      </Text>

      <AuthInput
        icon="mail-outline"
        placeholder="Email address"
        value={email}
        onChangeText={(v) => { setEmail(v); setEmailError(null); setFormError(null); }}
        error={emailError}
        autoCapitalize="none"
        autoCorrect={false}
        keyboardType="email-address"
        autoComplete="email"
        textContentType="emailAddress"
        returnKeyType="send"
        onSubmitEditing={handleSend}
      />

      {formError ? (
        <Text accessibilityRole="alert" style={{ color: colors.danger, marginBottom: 12, textAlign: 'center' }}>
          {formError}
        </Text>
      ) : null}

      <View style={{ marginTop: 8 }}>
        <PrimaryButton label="Send reset link" onPress={handleSend} loading={loading} />
      </View>
    </AuthScreen>
  );
}
