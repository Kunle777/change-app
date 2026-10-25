import { useTheme } from '../contexts/ThemeContext';

export const lightColors = {
  background: '#F8FAFC',
  surface: '#FFFFFF',
  text: '#111827',
  textMuted: '#6B7280',
  border: '#E5E7EB',
  primary: '#4F46E5',
  primaryDeep: '#312E81',
  accent: '#F59E0B',
  success: '#10B981',
  danger: '#EF4444',
  heroBg: '#1A1636',
  primarySoft: '#EEF0FF',
  warmSurface: '#FFF7ED',
  warmBorder: '#E5C99B',
  lavenderSurface: '#F5F3FF',
} as const;

export const darkColors = {
  background: '#0B0A1F',
  surface: '#15132E',
  text: '#EDEDF7',
  textMuted: '#A5A3C4',
  border: '#322F55',
  primary: '#6D63FF',
  primaryDeep: '#4F46E5',
  accent: '#F59E0B',
  success: '#10B981',
  danger: '#F87171',
  heroBg: '#12102B',
  primarySoft: '#1E1B4B',
  warmSurface: '#2A2218',
  warmBorder: '#5C4A2B',
  lavenderSurface: '#1B1840',
} as const;

export type ThemeColors = { [Key in keyof typeof lightColors]: string };

export function useColors(): ThemeColors {
  const { resolvedTheme } = useTheme();
  return resolvedTheme === 'dark' ? darkColors : lightColors;
}
