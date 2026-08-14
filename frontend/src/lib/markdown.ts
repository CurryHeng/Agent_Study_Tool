import katex from 'katex'

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function renderMath(display: boolean, formula: string): string {
  try {
    return katex.renderToString(formula.trim(), { displayMode: display, throwOnError: false })
  } catch {
    return `<pre>${escapeHtml(formula.trim())}</pre>`
  }
}

/** 渲染 markdown + LaTeX（$$..$$、$..$、**bold**、`code`、标题、列表）为 HTML */
export function renderMarkdown(raw: string): string {
  let text = raw || ''
  text = text.replace(/\\\(/g, '$').replace(/\\\)/g, '$')
  text = text.replace(/\\\[/g, '$$').replace(/\\\]/g, '$$')

  const formulas: string[] = []
  text = text.replace(/\$\$([\s\S]*?)\$\$/g, (_, f: string) => {
    formulas.push(renderMath(true, f))
    return `\u0000F${formulas.length - 1}\u0000`
  })
  text = text.replace(/\$([\s\S]+?)\$/g, (_, f: string) => {
    if (/^\d[\d,.]*$/.test(f.trim())) return `$${f}$`
    formulas.push(renderMath(false, f))
    return `\u0000F${formulas.length - 1}\u0000`
  })

  // 安全：公式已抽离为占位符，剩余用户/AI 文本整体转义，防止 v-html 注入 HTML/<script>
  text = escapeHtml(text)

  text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  text = text.replace(/`([^`]+)`/g, '<code>$1</code>')

  const lines = text.split('\n')
  const result: string[] = []
  let inList = false
  let inOl = false
  let para: string[] = []

  function flushPara() {
    if (para.length) {
      result.push(`<p>${para.join('<br>')}</p>`)
      para = []
    }
  }
  function closeLists() {
    if (inList) {
      result.push('</ul>')
      inList = false
    }
    if (inOl) {
      result.push('</ol>')
      inOl = false
    }
  }

  for (const line of lines) {
    if (!line.trim()) {
      closeLists()
      flushPara()
      continue
    }
    let m = line.match(/^###\s+(.+)/)
    if (m) {
      closeLists()
      flushPara()
      result.push(`<h3>${m[1]}</h3>`)
      continue
    }
    m = line.match(/^##\s+(.+)/)
    if (m) {
      closeLists()
      flushPara()
      result.push(`<h2>${m[1]}</h2>`)
      continue
    }
    m = line.match(/^#\s+(.+)/)
    if (m) {
      closeLists()
      flushPara()
      result.push(`<h1>${m[1]}</h1>`)
      continue
    }
    m = line.match(/^\s*[-*]\s+(.+)/)
    if (m) {
      flushPara()
      if (!inList) {
        result.push('<ul>')
        inList = true
      }
      result.push(`<li>${m[1]}</li>`)
      continue
    }
    m = line.match(/^\s*\d+\.\s+(.+)/)
    if (m) {
      flushPara()
      if (!inOl) {
        result.push('<ol>')
        inOl = true
      }
      result.push(`<li>${m[1]}</li>`)
      continue
    }
    closeLists()
    para.push(line.trim())
  }
  closeLists()
  flushPara()

  return result.join('\n').replace(/\u0000F(\d+)\u0000/g, (_, i: string) => formulas[+i] || '')
}
