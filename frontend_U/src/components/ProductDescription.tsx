import './ProductDescription.css'

/** Format plain text only; React escapes every line, including HTML-like input. */
export default function ProductDescription({ text }: { text?: string | null }) {
  const blocks: { kind: 'text' | 'list'; lines: string[] }[] = []
  let current: (typeof blocks)[number] | undefined
  for (const line of (text || '').split(/\r\n|\n|\r/)) {
    if (!line.trim()) { current = undefined; continue }
    const bullet = line.match(/^\s*[*•-]\s+(.+)$/)
    const kind = bullet ? 'list' : 'text'
    if (!current || current.kind !== kind) {
      current = { kind, lines: [] }
      blocks.push(current)
    }
    current.lines.push(bullet ? bullet[1] : line)
  }
  return <div className="product-description">
    {blocks.length ? blocks.map((block, index) => block.kind === 'list'
      ? <ul key={index}>{block.lines.map((line, i) => <li key={i}>{line}</li>)}</ul>
      : <p key={index}>{block.lines.join('\n')}</p>)
      : <p>Sin descripción disponible.</p>}
  </div>
}
