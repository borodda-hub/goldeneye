/**
 * Minimal, injection-safe renderer for the inline markdown the LLM
 * narratives emit (demo-polish sprint): `**bold**` and `*italic*` only.
 * Pure string splitting into React nodes — no HTML parsing, no
 * dangerouslySetInnerHTML, so model output can never inject markup.
 * Anything else (links, headers, code) renders as literal text on purpose.
 */

const TOKEN = /(\*\*[^*\n]+\*\*|\*[^*\n]+\*)/g;

export function InlineMarkdown({ text }: { text: string }) {
  const parts = text.split(TOKEN);
  return (
    <>
      {parts.map((part, i) => {
        const key = `${i}-${part.slice(0, 12)}`;
        if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
          return (
            <strong key={key} className="font-semibold text-ink-1">
              {part.slice(2, -2)}
            </strong>
          );
        }
        if (part.startsWith("*") && part.endsWith("*") && part.length > 2) {
          return <em key={key}>{part.slice(1, -1)}</em>;
        }
        return part;
      })}
    </>
  );
}
