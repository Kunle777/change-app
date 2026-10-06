import React from 'react';
import ElvynNeutral from '../assets/mascot/evelyn-neutral.svg';
import ElvynSupportive from '../assets/mascot/evelyn-supportive.svg';

type MascotVariant = 'neutral' | 'supportive';

interface ElvynMascotProps {
  variant: MascotVariant;
  size?: number;
}

const VARIANTS: Record<MascotVariant, React.FC<any>> = {
  neutral: ElvynNeutral,
  supportive: ElvynSupportive,
};

export default function ElvynMascot({ variant, size = 100 }: ElvynMascotProps) {
  const MascotSvg = VARIANTS[variant] ?? VARIANTS.neutral;
  return <MascotSvg width={size} height={size * (340 / 300)} />;
}
