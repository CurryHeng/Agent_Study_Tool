/**
 * 选择题解析 & 正确答案提取测试
 */

import { describe, it, expect } from 'vitest'

interface Choice {
  letter: string
  text: string
}

function parseChoices(problem: string): Choice[] | null {
  const fullMatch = problem.match(/\(([A-D])\)\s*(.+?)(?=\s*\([A-D]\)|$)/gs)
  if (!fullMatch || fullMatch.length < 2) return null
  const choices: Choice[] = []
  for (const m of fullMatch) {
    const m2 = m.match(/^\(([A-D])\)\s*(.+)/s)
    if (m2) choices.push({ letter: m2[1], text: m2[2].trim() })
  }
  return choices.length >= 2 ? choices : null
}

function parseCorrectLetter(correctAnswer: string): string | null {
  const stripped = correctAnswer.replace(/\*\*/g, '').trim()
  const m = stripped.match(/^[\(（]?([A-D])[\)）]?/)
  return m ? m[1] : null
}

function parseCorrectLetterExtended(answerText: string): string | null {
  // Extended patterns for AI-generated answers
  const patterns = [
    /正确\s*答案\s*[：:]\s*([A-D])/,
    /答案\s*[：:]\s*([A-D])/,
    /故?选\s*([A-D])/,
    /应?选\s*([A-D])/,
    /\(([A-D])\)\s*正确/,
    /正确\s*选项\s*[：:]\s*([A-D])/,
  ]
  for (const p of patterns) {
    const m = answerText.match(p)
    if (m) return m[1]
  }
  // Simple prefix match
  const stripped = answerText.replace(/\*\*/g, '').trim()
  const m = stripped.match(/^[\(（]?([A-D])[\)）]?/)
  if (m && stripped.length < 10) return m[1]
  return null
}

// ====== Tests ======

describe('parseChoices', () => {
  it('should parse standard choices', () => {
    const problem = '求极限\n(A) 0\n(B) 1\n(C) ∞\n(D) 不存在'
    const choices = parseChoices(problem)
    expect(choices).not.toBeNull()
    expect(choices).toHaveLength(4)
    expect(choices![0]).toEqual({ letter: 'A', text: '0' })
    expect(choices![2]).toEqual({ letter: 'C', text: '∞' })
  })

  it('should parse choices with LaTeX', () => {
    const problem = '(A) $\\frac{1}{2}$\n(B) $1$\n(C) $2$\n(D) $\\infty$'
    const choices = parseChoices(problem)
    expect(choices).not.toBeNull()
    expect(choices).toHaveLength(4)
    expect(choices![0].text).toBe('$\\frac{1}{2}$')
  })

  it('should return null for < 2 choices', () => {
    expect(parseChoices('just text (A) one option')).toBeNull()
    expect(parseChoices('no choices here')).toBeNull()
  })

  it('should handle choices with multiline text', () => {
    const problem = '(A) This is a\nlong option text\n(B) Short option'
    const choices = parseChoices(problem)
    expect(choices).not.toBeNull()
    expect(choices).toHaveLength(2)
    expect(choices![0].text).toContain('long option text')
  })

  it('should return null for empty string', () => {
    expect(parseChoices('')).toBeNull()
  })

  it('should handle Chinese parentheses in choices', () => {
    // Note: current implementation only matches ASCII ()
    const problem = '（A） 选项1\n（B） 选项2'
    const choices = parseChoices(problem)
    // Chinese parens not supported by current regex
    expect(choices).toBeNull()
  })
})

describe('parseCorrectLetter', () => {
  it('should parse simple letter', () => {
    expect(parseCorrectLetter('B')).toBe('B')
  })

  it('should parse (B)', () => {
    expect(parseCorrectLetter('(B)')).toBe('B')
  })

  it('should parse with markdown bold', () => {
    expect(parseCorrectLetter('**B**')).toBe('B')
  })

  it('should parse （C） with Chinese parens', () => {
    expect(parseCorrectLetter('（C）')).toBe('C')
  })

  it('should return null for non-letter', () => {
    expect(parseCorrectLetter('正确答案')).toBeNull()
    expect(parseCorrectLetter('$x=1$')).toBeNull()
  })
})

describe('parseCorrectLetterExtended', () => {
  it('should match "正确答案：B"', () => {
    expect(parseCorrectLetterExtended('正确答案：B')).toBe('B')
  })

  it('should match "答案：D"', () => {
    expect(parseCorrectLetterExtended('答案：D')).toBe('D')
  })

  it('should match "故选A"', () => {
    expect(parseCorrectLetterExtended('故选A')).toBe('A')
  })

  it('should match "应选C"', () => {
    expect(parseCorrectLetterExtended('应选C')).toBe('C')
  })

  it('should match "(B) 正确"', () => {
    expect(parseCorrectLetterExtended('(B) 正确')).toBe('B')
  })

  it('should match "正确选项：A"', () => {
    expect(parseCorrectLetterExtended('正确选项：A')).toBe('A')
  })

  it('should return null for complex text', () => {
    expect(parseCorrectLetterExtended('这道题的正确答案是选择B，因为...')).toBeNull()
  })
})
