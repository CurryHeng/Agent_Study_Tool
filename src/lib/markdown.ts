import katex from 'katex'

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function renderDisplay(f: string): string {
  try { return katex.renderToString(f.trim(), { displayMode: true, throwOnError: false }) }
  catch { return `<pre>${escapeHtml(f.trim())}</pre>` }
}

function renderInline(f: string): string {
  try { return katex.renderToString(f.trim(), { displayMode: false, throwOnError: false }) }
  catch { return escapeHtml(f.trim()) }
}

/** Render inline markdown: **bold** and `code` */
export function processInlineMarkdown(text: string): string {
  let html = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>')
  return html
}

/**
 * Render LaTeX formulas in text (for use in QuestionCard content).
 * Handles $$...$$, $...$, and their \(\) \[\] variants.
 * Also processes **bold** markers and converts double-newlines to paragraph breaks.
 */
export function renderContent(text: string): string {
  // Normalize delimiters
  text = text.replace(/\\\(/g, '$').replace(/\\\)/g, '$')
  text = text.replace(/\\\[/g, '$$').replace(/\\\]/g, '$$')

  // Extract display math $$...$$ (multiline)
  const formulas: string[] = []
  text = text.replace(/\$\$([\s\S]*?)\$\$/g, (_, f) => {
    formulas.push(renderDisplay(f))
    return `\x00F${formulas.length - 1}\x00`
  })

  // Extract inline math $...$ (now multiline-aware, after $$ removed)
  text = text.replace(/\$([\s\S]+?)\$/g, (_, f) => {
    if (/^\d[\d,.]*$/.test(f.trim())) return `$${f}$`
    formulas.push(renderInline(f))
    return `\x00F${formulas.length - 1}\x00`
  })

  // Process bold
  text = processInlineMarkdown(text)

  // Split by double newlines into paragraphs, preserve single newlines as <br>
  const paragraphs = text.split(/\n{2,}/)
  const result = paragraphs
    .map((p) => {
      const trimmed = p.trim()
      if (!trimmed) return ''
      // Single newlines within paragraph become <br>
      const withBreaks = trimmed.replace(/\n/g, '<br>')
      return `<p>${withBreaks}</p>`
    })
    .filter(Boolean)
    .join('\n')

  // Restore formulas
  return result.replace(/\x00F(\d+)\x00/g, (_, i) => formulas[+i] || '')
}

/**
 * Render AI-generated content (markdown + LaTeX) to HTML.
 */
export function renderMarkdown(raw: string): string {
  // Normalize delimiters
  let text = raw.replace(/\\\(/g, '$').replace(/\\\)/g, '$')
  text = text.replace(/\\\[/g, '$$').replace(/\\\]/g, '$$')

  const formulas: string[] = []

  // Display math
  text = text.replace(/\$\$([\s\S]*?)\$\$/g, (_, f) => {
    formulas.push(renderDisplay(f))
    return `\x00F${formulas.length - 1}\x00`
  })

  // Inline math (multiline-aware, after $$ removed)
  text = text.replace(/\$([\s\S]+?)\$/g, (_, f) => {
    if (/^\d[\d,.]*$/.test(f.trim())) return `$${f}$`
    formulas.push(renderInline(f))
    return `\x00F${formulas.length - 1}\x00`
  })

  // Line-by-line markdown parsing
  const lines = text.split('\n')
  const result: string[] = []
  let inList = false
  let inOl = false
  let paragraphBuf: string[] = []

  function flushParagraph() {
    if (paragraphBuf.length > 0) {
      const joined = paragraphBuf.join('<br>')
      if (joined.trim()) result.push(`<p>${joined.trim()}</p>`)
      paragraphBuf = []
    }
  }

  function closeLists() {
    if (inList) { result.push('</ul>'); inList = false }
    if (inOl) { result.push('</ol>'); inOl = false }
  }

  for (const line of lines) {
    if (line.trim() === '') {
      closeLists()
      flushParagraph()
      continue
    }

    // ### heading
    let m = line.match(/^###\s+(.+)/)
    if (m) { closeLists(); flushParagraph(); result.push(`<h3>${processInlineMarkdown(m[1])}</h3>`); continue }

    // ## heading
    m = line.match(/^##\s+(.+)/)
    if (m) { closeLists(); flushParagraph(); result.push(`<h2>${processInlineMarkdown(m[1])}</h2>`); continue }

    // - unordered list
    const ul = line.match(/^[\s]*[-*]\s+(.+)/)
    if (ul) {
      flushParagraph()
      if (!inList) { result.push('<ul>'); inList = true }
      if (inOl) { result.push('</ol>'); inOl = false }
      result.push(`<li>${processInlineMarkdown(ul[1])}</li>`)
      continue
    }

    // 1. ordered list
    const ol = line.match(/^[\s]*\d+\.\s+(.+)/)
    if (ol) {
      flushParagraph()
      if (!inOl) { result.push('<ol>'); inOl = true }
      if (inList) { result.push('</ul>'); inList = false }
      result.push(`<li>${processInlineMarkdown(ol[1])}</li>`)
      continue
    }

    if (inList || inOl) {
      // Multi-line list item continuation
      const lastIdx = result.length - 1
      if (lastIdx >= 0 && result[lastIdx].endsWith('</li>')) {
        result[lastIdx] = result[lastIdx].replace('</li>', `<br>${processInlineMarkdown(line.trim())}</li>`)
        continue
      }
    }

    closeLists()
    paragraphBuf.push(processInlineMarkdown(line.trim()))
  }

  closeLists()
  flushParagraph()

  return result.join('\n').replace(/\x00F(\d+)\x00/g, (_, i) => formulas[+i] || '')
}
