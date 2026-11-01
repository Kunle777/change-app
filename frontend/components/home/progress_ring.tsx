import { View } from 'react-native';
import Svg, { Circle } from 'react-native-svg';
import AppText from '../ui/AppText';

type Props = { percent: number; size?: number; stroke?: number; color: string; track: string; textColor: string };

export default function ProgressRing({ percent, size = 76, stroke = 8, color, track, textColor }: Props) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const clamped = Math.max(0, Math.min(100, percent));
  return (
    <View style={{ width: size, height: size, alignItems: 'center', justifyContent: 'center' }}>
      <Svg width={size} height={size} style={{ position: 'absolute', transform: [{ rotate: '-90deg' }] }}>
        <Circle cx={size / 2} cy={size / 2} r={r} stroke={track} strokeWidth={stroke} fill="none" />
        <Circle
          cx={size / 2} cy={size / 2} r={r} stroke={color} strokeWidth={stroke} fill="none"
          strokeLinecap="round" strokeDasharray={[c, c]} strokeDashoffset={c * (1 - clamped / 100)}
        />
      </Svg>
      <AppText variant="title" style={{ color: textColor, textAlign: 'center' }}>
        {clamped}%
      </AppText>
    </View>
  );
}