import { useEffect, useRef } from 'react';
import { Animated, Easing, Text, View } from 'react-native';
import { useColors } from '../../theme/colors';

export default function TypingIndicator() {
  const colors = useColors();
  const dots = useRef([0, 1, 2].map(() => new Animated.Value(0.3))).current;

  useEffect(() => {
    const loops = dots.map((dot, index) =>
      Animated.loop(
        Animated.sequence([
          Animated.delay(index * 160),
          Animated.timing(dot, { toValue: 1, duration: 320, easing: Easing.out(Easing.quad), useNativeDriver: true }),
          Animated.timing(dot, { toValue: 0.3, duration: 320, easing: Easing.in(Easing.quad), useNativeDriver: true }),
          Animated.delay((2 - index) * 160),
        ]),
      ),
    );
    loops.forEach((loop) => loop.start());
    return () => loops.forEach((loop) => loop.stop());
  }, [dots]);

  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', marginHorizontal: 16, marginBottom: 10 }}>
      <View
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          backgroundColor: colors.surface,
          borderWidth: 1,
          borderColor: colors.border,
          borderRadius: 18,
          paddingHorizontal: 14,
          paddingVertical: 12,
        }}
      >
        {dots.map((dot, index) => (
          <Animated.View
            key={index}
            style={{
              width: 7,
              height: 7,
              borderRadius: 4,
              marginRight: index === 2 ? 0 : 5,
              backgroundColor: colors.primary,
              opacity: dot,
            }}
          />
        ))}
        <Text style={{ color: colors.textMuted, fontSize: 12, marginLeft: 10 }}>Elvyn is thinking…</Text>
      </View>
    </View>
  );
}
