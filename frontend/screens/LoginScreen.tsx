import { useState } from 'react';
import { View, Text, TextInput, StyleSheet, TouchableOpacity, Alert } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { supabase } from '../services/supabase';
import { RootStackParamList } from '../navigation/AppNavigator';
import { signInWithGoogle } from '../services/google_auth';

type Props = NativeStackScreenProps<RootStackParamList, 'Login'>;

export default function LoginScreen({ navigation }: Props) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);

  const handleLogin = async () => {
    setLoading(true);
    setError('');
    try {
      const { error: authError } = await supabase.auth.signInWithPassword({ email, password });
      if (authError) {
        setError(authError.message);
        return;
      }

      navigation.replace('MainTabs');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unable to log in. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  async function handleGoogleSignIn() {
    setGoogleLoading(true);
    try {
      const session = await signInWithGoogle();
      if (session) {
        navigation.replace('MainTabs');
      }
    } catch (err: any) {
      Alert.alert('Sign-in failed', err.message ?? 'Please try again.');
    } finally {
      setGoogleLoading(false);
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Elvyn</Text>
      <TextInput
        style={styles.input}
        placeholder="Email"
        value={email}
        onChangeText={setEmail}
        autoCapitalize="none"
        placeholderTextColor="#999"
      />
      <TextInput
        style={styles.input}
        placeholder="Password"
        value={password}
        onChangeText={setPassword}
        secureTextEntry
        placeholderTextColor="#999"
      />
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <TouchableOpacity style={styles.button} onPress={handleLogin} disabled={loading}>
        <Text style={styles.buttonText}>{loading ? 'Logging in...' : 'Log In'}</Text>
      </TouchableOpacity>
      <TouchableOpacity onPress={() => navigation.navigate('Register')}>
        <Text style={{ marginTop: 16, textAlign: 'center' }}>Don't have an account? Register</Text>
      </TouchableOpacity>
      <TouchableOpacity onPress={() => navigation.navigate('ForgotPassword')}>
        <Text style={{ marginTop: 12, textAlign: 'center', color: '#555' }}>Forgot password?</Text>
      </TouchableOpacity>
      <TouchableOpacity onPress={handleGoogleSignIn} disabled={googleLoading}>
        <Text>{googleLoading ? 'Connecting…' : 'Continue with Google'}</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', padding: 24 },
  title: { fontSize: 28, fontWeight: 'bold', marginBottom: 32, textAlign: 'center' },
  input: { borderWidth: 1, borderColor: '#ccc', borderRadius: 8, padding: 12, marginBottom: 12 },
  button: { backgroundColor: '#333', padding: 14, borderRadius: 8, marginTop: 12 },
  buttonText: { color: '#fff', textAlign: 'center', fontWeight: '600' },
  error: { color: 'red', marginBottom: 8 },
});
