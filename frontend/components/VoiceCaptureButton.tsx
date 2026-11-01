import { useState } from 'react';
import { Alert, Text, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import {
  startListening,
  stopListening,
  requestSpeechPermissions,
  useSpeechRecognitionEvent,
} from '../services/VoiceCapture';
import { useColors } from '../theme/colors';

type Props = {
  onTranscript: (text: string) => void;
  onFinalTranscript?: (text: string) => void;
};

export default function VoiceCaptureButton({ onTranscript, onFinalTranscript }: Props) {
  const colors = useColors();
  const [isListening, setIsListening] = useState(false);

  // These hooks subscribe to native events for as long as this component
  // is mounted — they don't need to be inside handleStart/handleStop.
  useSpeechRecognitionEvent('start', () => setIsListening(true));

  useSpeechRecognitionEvent('end', () => setIsListening(false));

  useSpeechRecognitionEvent('result', (event) => {
    // Android can return multiple final results across a session — always
    // take the latest one, don't assume result[0] is the whole transcript.
    const latest = event.results[0]?.transcript;
    if (latest) {
      onTranscript(latest);
      if (event.isFinal) onFinalTranscript?.(latest);
    }
  });

  useSpeechRecognitionEvent('error', (event) => {
    console.warn('Speech recognition error:', event.error, event.message);
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
      onPress={handlePress}
      accessibilityRole="button"
      accessibilityLabel={isListening ? 'Stop voice capture' : 'Start voice capture'}
      style={{
        minHeight: 44,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: isListening ? `${colors.danger}18` : colors.primarySoft,
        paddingHorizontal: 16,
        borderRadius: 22,
      }}
    >
      <Ionicons
        name={isListening ? 'stop-circle-outline' : 'mic-outline'}
        size={18}
        color={isListening ? colors.danger : colors.primary}
      />
      <Text
        maxFontSizeMultiplier={1.2}
        style={{
          color: isListening ? colors.danger : colors.primary,
          fontSize: 14,
          lineHeight: 20,
          fontWeight: '600',
          marginLeft: 7,
        }}
      >
        {isListening ? 'Stop' : 'Speak'}
      </Text>
    </TouchableOpacity>
  );
}
