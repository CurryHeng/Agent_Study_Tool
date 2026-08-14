import { describe, expect, it } from 'vitest'
import { renderMarkdown } from '../lib/markdown'

describe('renderMarkdown', () => {
  it('转义 HTML，防止 XSS 注入（回归：v-html 直接注入未消毒内容）', () => {
    const html = renderMarkdown('<script>alert(1)</script><img src=x onerror=alert(1)>')
    expect(html).not.toContain('<script>')
    expect(html).not.toContain('<img')
    expect(html).toContain('&lt;script&gt;')
  })

  it('转义标题/加粗文本中的 HTML', () => {
    const html = renderMarkdown('# <b>标题</b>\n**<i>粗体</i>**')
    expect(html).not.toContain('<b>标题</b>')
    expect(html).toContain('&lt;b&gt;')
    expect(html).toContain('<strong>&lt;i&gt;粗体&lt;/i&gt;</strong>')
  })

  it('正常渲染 markdown 语法', () => {
    expect(renderMarkdown('**粗体**')).toContain('<strong>粗体</strong>')
    expect(renderMarkdown('`code`')).toContain('<code>code</code>')
    expect(renderMarkdown('- 项目')).toContain('<li>项目</li>')
  })

  it('正常渲染 KaTeX 公式', () => {
    expect(renderMarkdown('$x^2$')).toContain('katex')
  })
})
