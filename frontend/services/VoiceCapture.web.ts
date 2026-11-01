import type { useSpeechRecognitionEvent as useNativeSpeechRecognitionEvent } from 'expo-speech-recognition';

export async function requestSpeechPermissions(): Promise<boolean> {
  return false;
}

export function startListening(): void {}

export function stopListening(): void {}

export const useSpeechRecognitionEvent: typeof useNativeSpeechRecognitionEvent = () => {};
