/**
 * 标准化 LaTeX — 修复双重转义的反斜杠
 * JSON 中的 \\\\ 变成 \\, 实际需要 \
 */
export function normalizeLatex(text: string): string {
  if (!text) return ''
  // 修复双重转义: \\ → \
  return text.replace(/\\\\/g, '\\')
}

/**
 * 将 Markdown/LaTeX 文本转为纯文本预览
 */
export function stripMarkdown(text: string): string {
  if (!text) return ''

  // 先归一化反斜杠
  let result = normalizeLatex(text)

  // 去掉 $$...$$ 和 $...$ 包裹（保留内容核心文字）
  result = result.replace(/\$\$([\s\S]*?)\$\$/g, (_: string, f: string) => {
    return f.replace(/\\[a-zA-Z]+/g, '').replace(/[{}_^]/g, '').trim()
  })
  result = result.replace(/\$([^$\n]+?)\$/g, (_: string, f: string) => {
    return f.replace(/\\[a-zA-Z]+/g, '').replace(/[{}_^]/g, '').trim()
  })

  // 去掉剩余 LaTeX 命令
  result = result.replace(/\\[a-zA-Z]+(\{[^}]*\})*/g, '')
  result = result.replace(/[{}]/g, '')

  // 去掉 Markdown 格式
  result = result.replace(/\*\*(.+?)\*\*/g, '$1')
  result = result.replace(/\*(.+?)\*/g, '$1')
  result = result.replace(/`([^`]+)`/g, '$1')
  result = result.replace(/^#{1,6}\s+/gm, '')
  result = result.replace(/^>\s?/gm, '')
  result = result.replace(/^[\s]*[-*+]\s+/gm, '')
  result = result.replace(/^[\s]*\d+\.\s+/gm, '')

  // 去掉 HTML 和多余空白
  result = result.replace(/<[^>]+>/g, '')
  result = result.replace(/\\/g, '')
  result = result.replace(/\s{2,}/g, ' ')
  result = result.trim()

  return result
}
