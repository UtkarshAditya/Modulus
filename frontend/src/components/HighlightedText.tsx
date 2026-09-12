interface Span {
  start: number
  end: number
  severity?: string
  id?: number
}

const SEVERITY_HIGHLIGHT: Record<string, string> = {
  CRITICAL: 'bg-red-300',
  HIGH: 'bg-orange-300',
  MEDIUM: 'bg-amber-200',
  LOW: 'bg-slate-300',
}

/** Renders `text` with each non-empty span wrapped in a highlight. Spans
 * come from RuleHit.evidence, which indexes into `${title}\n${description}`
 * (see apps.moderation.tasks — NormalizedDoc.combine(title, description)),
 * so callers must pass that same combined string, not description alone.
 */
export function HighlightedText({
  text,
  spans,
  activeId,
}: {
  text: string
  spans: Span[]
  activeId?: number | null
}) {
  const ranges = spans
    .filter((s) => s.end > s.start)
    .slice()
    .sort((a, b) => a.start - b.start)

  const parts: { text: string; span?: Span }[] = []
  let cursor = 0
  for (const span of ranges) {
    const start = Math.max(span.start, cursor)
    const end = Math.max(span.end, start)
    if (start > cursor) parts.push({ text: text.slice(cursor, start) })
    if (end > start) parts.push({ text: text.slice(start, end), span })
    cursor = Math.max(cursor, end)
  }
  if (cursor < text.length) parts.push({ text: text.slice(cursor) })

  return (
    <p className="whitespace-pre-wrap text-sm text-slate-700">
      {parts.map((part, i) =>
        part.span ? (
          <mark
            key={i}
            id={part.span.id !== undefined ? `evidence-${part.span.id}` : undefined}
            className={`rounded px-0.5 text-slate-900 transition-colors ${
              SEVERITY_HIGHLIGHT[part.span.severity ?? 'MEDIUM']
            } ${activeId !== undefined && activeId === part.span.id ? 'ring-2 ring-slate-900' : ''}`}
          >
            {part.text}
          </mark>
        ) : (
          <span key={i}>{part.text}</span>
        ),
      )}
    </p>
  )
}
