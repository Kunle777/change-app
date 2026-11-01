import type { TextStyle } from 'react-native';

export const typography = {
  display: {
    fontSize: 26,
    lineHeight: 32,
    fontWeight: '700',
  },
  title: {
    fontSize: 18,
    lineHeight: 24,
    fontWeight: '600',
  },
  body: {
    fontSize: 14,
    lineHeight: 20,
    fontWeight: '400',
  },
  secondary: {
    fontSize: 13,
    lineHeight: 18,
    fontWeight: '400',
  },
  caption: {
    fontSize: 12,
    lineHeight: 16,
    fontWeight: '400',
  },
  wordmark: {
    fontSize: 14,
    lineHeight: 18,
    fontWeight: '700',
    letterSpacing: 3,
  },
  greeting: {
    fontSize: 16,
    lineHeight: 22,
    fontWeight: '400',
  },
} satisfies Record<string, TextStyle>;

export type TypographyVariant = keyof typeof typography;

export const maxFontSizeMultiplier: Record<TypographyVariant, number> = {
  display: 1.2,
  title: 1.2,
  body: 1.4,
  secondary: 1.4,
  caption: 1.2,
  wordmark: 1.2,
  greeting: 1.2,
};
