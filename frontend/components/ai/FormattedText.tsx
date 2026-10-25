import { Text, View } from 'react-native';

type Props = { text: string; color: string; bulletColor: string };

function renderInline(line: string, color: string) {
  const parts = line.split(/(\*\*[^*]+\*\*)/g).filter(Boolean);
  return parts.map((part, index) =>
    part.startsWith('**') && part.endsWith('**') ? (
      <Text key={index} style={{ fontWeight: '700', color }}>
        {part.slice(2, -2)}
      </Text>
    ) : (
      <Text key={index}>{part}</Text>
    ),
  );
}

/** Minimal formatting for model replies: "- " / "* " bullets and **bold**. */
export default function FormattedText({ text, color, bulletColor }: Props) {
  const lines = text.split('\n');
  return (
    <View>
      {lines.map((raw, index) => {
        const line = raw.trimEnd();
        if (!line.trim()) return <View key={index} style={{ height: 6 }} />;
        const bullet = /^\s*[-*•]\s+(.*)$/.exec(line);
        if (bullet) {
          return (
            <View key={index} style={{ flexDirection: 'row', marginTop: 3 }}>
              <Text style={{ color: bulletColor, marginRight: 8, lineHeight: 21 }}>•</Text>
              <Text style={{ color, fontSize: 15, lineHeight: 21, flex: 1 }}>
                {renderInline(bullet[1], color)}
              </Text>
            </View>
          );
        }
        return (
          <Text key={index} style={{ color, fontSize: 15, lineHeight: 21 }}>
            {renderInline(line, color)}
          </Text>
        );
      })}
    </View>
  );
}
