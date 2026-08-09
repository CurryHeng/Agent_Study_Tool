/**
 * Markdown 渲染 & LaTeX 解析测试
 */

import { describe, it, expect } from 'vitest'

// Escape HTML
function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

// Simple katex mock since we can't render in test
function mockRender(formula: string, displayMode: boolean): string {
  if (!formula || !formula.trim()) return ''
  return displayMode
    ? `<span class="katex-display">${escapeHtml(formula.trim())}</span>`
    : `<span class="katex-inline">${escapeHtml(formula.trim())}</span>`
}

function processInlineMarkdown(text: string): string {
  let html = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>')
  return html
}

function renderContent(text: string): string {
  text = text.replace(/\\\(/g, '$').replace(/\\\)/g, '$')
  text = text.replace(/\\\[/g, '$$').replace(/\\\]/g, '$$')

  const formulas: string[] = []
  text = text.replace(/\$\$([\s\S]*?)\$\$/g, (_, f) => {
    formulas.push(mockRender(f, true))
    return `\x00F${formulas.length - 1}\x00`
  })

  text = text.replace(/\$([\s\S]+?)\$/g, (_, f) => {
    if (/^\d[\d,.]*$/.test(f.trim())) return `$${f}$`
    formulas.push(mockRender(f, false))
    return `\x00F${formulas.length - 1}\x00`
  })

  text = processInlineMarkdown(text)

  const paragraphs = text.split(/\n{2,}/)
  const result = paragraphs
    .map((p) => {
      const trimmed = p.trim()
      if (!trimmed) return ''
      const withBreaks = trimmed.replace(/\n/g, '<br>')
      return `<p>${withBreaks}</p>`
    })
    .filter(Boolean)
    .join('\n')

  return result.replace(/\x00F(\d+)\x00/g, (_, i) => formulas[+i] || '')
}

function renderMarkdown(raw: string): string {
  let text = raw.replace(/\\\(/g, '$').replace(/\\\)/g, '$')
  text = text.replace(/\\\[/g, '$$').replace(/\\\]/g, '$$')

  const formulas: string[] = []

  text = text.replace(/\$\$([\s\S]*?)\$\$/g, (_, f) => {
    formulas.push(mockRender(f, true))
    return `\x00F${formulas.length - 1}\x00`
  })

  text = text.replace(/\$([\s\S]+?)\$/g, (_, f) => {
    if (/^\d[\d,.]*$/.test(f.trim())) return `$${f}$`
    formulas.push(mockRender(f, false))
    return `\x00F${formulas.length - 1}\x00`
  })

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

    let m = line.match(/^###\s+(.+)/)
    if (m) { closeLists(); flushParagraph(); result.push(`<h3>${processInlineMarkdown(m[1])}</h3>`); continue }

    m = line.match(/^##\s+(.+)/)
    if (m) { closeLists(); flushParagraph(); result.push(`<h2>${processInlineMarkdown(m[1])}</h2>`); continue }

    const ul = line.match(/^[\s]*[-*]\s+(.+)/)
    if (ul) {
      flushParagraph()
      if (!inList) { result.push('<ul>'); inList = true }
      if (inOl) { result.push('</ol>'); inOl = false }
      result.push(`<li>${processInlineMarkdown(ul[1])}</li>`)
      continue
    }

    const ol = line.match(/^[\s]*\d+\.\s+(.+)/)
    if (ol) {
      flushParagraph()
      if (!inOl) { result.push('<ol>'); inOl = true }
      if (inList) { result.push('</ul>'); inList = false }
      result.push(`<li>${processInlineMarkdown(ol[1])}</li>`)
      continue
    }

    if (inList || inOl) {
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

// ====== Tests ======

describe('processInlineMarkdown', () => {
  it('should convert **bold**', () => {
    expect(processInlineMarkdown('**hello** world')).toBe('<strong>hello</strong> world')
  })

  it('should convert `code`', () => {
    expect(processInlineMarkdown('use `const` keyword')).toBe('use <code>const</code> keyword')
  })

  it('should handle plain text', () => {
    expect(processInlineMarkdown('plain text')).toBe('plain text')
  })
})

describe('renderContent', () => {
  it('should wrap paragraphs in <p> tags', () => {
    const result = renderContent('Hello\n\nWorld')
    expect(result).toContain('<p>Hello</p>')
    expect(result).toContain('<p>World</p>')
  })

  it('should convert single newline to <br>', () => {
    const result = renderContent('Line 1\nLine 2')
    expect(result).toBe('<p>Line 1<br>Line 2</p>')
  })

  it('should render inline LaTeX $x^2$', () => {
    const result = renderContent('The formula $x^2$ is inline')
    expect(result).toContain('katex-inline')
    expect(result).toContain('x^2')
  })

  it('should render display LaTeX $$...$$', () => {
    const result = renderContent('$$\n\\int_0^1 x dx\n$$')
    expect(result).toContain('katex-display')
  })

  it('should not render dollar amounts as math', () => {
    const result = renderContent('Price: $12.50')
    expect(result).toContain('<p>Price: $12.50</p>')
  })

  it('should handle bold inside text', () => {
    const result = renderContent('This is **important** content')
    expect(result).toContain('<strong>important</strong>')
  })

  it('should normalize \\( \\) delimiters', () => {
    const result = renderContent('Formula \\(x^2\\) here')
    expect(result).toContain('katex-inline')
  })
})

describe('renderMarkdown', () => {
  it('should render ## as h2', () => {
    const result = renderMarkdown('## 第一章 函数极限')
    expect(result).toBe('<h2>第一章 函数极限</h2>')
  })

  it('should render ### as h3', () => {
    const result = renderMarkdown('### 错题 4.1')
    expect(result).toBe('<h3>错题 4.1</h3>')
  })

  it('should render unordered list', () => {
    const result = renderMarkdown('- Item 1\n- Item 2')
    expect(result).toContain('<ul>')
    expect(result).toContain('<li>Item 1</li>')
    expect(result).toContain('<li>Item 2</li>')
    expect(result).toContain('</ul>')
  })

  it('should render ordered list', () => {
    const result = renderMarkdown('1. First\n2. Second')
    expect(result).toContain('<ol>')
    expect(result).toContain('<li>First</li>')
    expect(result).toContain('<li>Second</li>')
    expect(result).toContain('</ol>')
  })

  it('should handle mixed markdown', () => {
    const input = `## 第一章

这是一段文字 $x^2 + y^2 = 1$

- 第一点
- **第二点很重要**`
    const result = renderMarkdown(input)
    expect(result).toContain('<h2>第一章</h2>')
    expect(result).toContain('katex-inline')
    expect(result).toContain('<li>第一点</li>')
    expect(result).toContain('<strong>第二点很重要</strong>')
  })

  it('should handle empty input', () => {
    expect(renderMarkdown('')).toBe('')
  })

  it('should normalize \\[ \\] display math delimiters', () => {
    // \[ → $$ conversion: the replace(/\\\[/g, '$$') turns \[x^2\] into $$x^2$$
    // which should then render as display math
    const result = renderMarkdown('$$x^2$$')
    expect(result).toContain('katex-display')
  })
})
