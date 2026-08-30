import { ExpoSpeechRecognitionModule, useSpeechRecognitionEvent } from 'expo-speech-recognition';

export async function requestSpeechPermissions(): Promise<boolean> {
  const result = await ExpoSpeechRecognitionModule.requestPermissionsAsync();
  return result.granted;
}

export function startListening() {
  ExpoSpeechRecognitionModule.start({
    lang: 'en-US',
    interimResults: true, // fires partial results as you speak, not just the final one
    continuous: true, // keeps listening until explicitly stopped, not just one phrase
  });
}

export function stopListening() {
  ExpoSpeechRecognitionModule.stop();
}

export { useSpeechRecognitionEvent };
