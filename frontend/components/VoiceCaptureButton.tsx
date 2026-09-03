import { useState } from 'react';
import { TouchableOpacity, Text, StyleSheet, Alert } from 'react-native';
import {
  startListening,
  stopListening,
  requestSpeechPermissions,
  useSpeechRecognitionEvent,
} from '../services/VoiceCapture';

type Props = {
  onTranscript: (text: string) => void;
};

export default function VoiceCaptureButton({ onTranscript }: Props) {
  const [isListening, setIsListening] = useState(false);

  // These hooks subscribe to native events for as long as this component
  // is mounted — they don't need to be inside handleStart/handleStop.
  useSpeechRecognitionEvent('start', () => setIsListening(true));

  useSpeechRecognitionEvent('end', () => setIsListening(false));

  useSpeechRecognitionEvent('result', (event) => {
    // Android can return multiple final results across a session — always
    // take the latest one, don't assume result[0] is the whole transcript.
    const latest = event.results[0]?.transcript;
    if (latest) onTranscript(latest);
  });

  useSpeechRecognitionEvent('error', (event) => {
    console.log('Speech recognition error:', event.error, event.message);
    setIsListening(false);
  });

  async function handlePress() {
    if (isListening) {
      stopListening();
      return;
    }

    const granted = await requestSpeechPermissions();
    if (!granted) {
      Alert.alert(
        'Microphone permission needed',
        'Enable microphone access in Settings to use voice capture.',
      );
      return;
    }

    startListening();
  }

  return (
    <TouchableOpacity
      style={[styles.button, isListening && styles.buttonActive]}
      onPress={handlePress}
    >
      <Text style={styles.buttonText}>{isListening ? '⏹ Stop' : '🎤 Speak'}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  button: {
    backgroundColor: '#eee',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 20,
    alignItems: 'center',
  },
  buttonActive: {
    backgroundColor: '#e74c3c',
  },
  buttonText: {
    fontWeight: '600',
    color: '#333',
  },
});
