/**
 * 中文章节排序 & 章节号解析测试
 */

import { describe, it, expect } from 'vitest'

const CN_NUM: Record<string, number> = {
  '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
  '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
}
const CN_NUM_REV: Record<string, number> = {
  '十一': 11, '十二': 12, '十三': 13, '十四': 14, '十五': 15,
  '十六': 16, '十七': 17, '十八': 18, '十九': 19, '二十': 20,
}

function parseChapterNumber(chapter: string): number {
  const m = chapter.match(/^第(.+?)章/)
  if (!m) return 999
  const cn = m[1]
  if (CN_NUM_REV[cn] !== undefined) return CN_NUM_REV[cn]
  let num = 0
  if (cn.startsWith('十')) {
    num = 10 + (CN_NUM[cn[1]] || 0)
  } else if (cn.endsWith('十')) {
    num = (CN_NUM[cn[0]] || 0) * 10
  } else if (cn.length === 3 && CN_NUM[cn[0]] && CN_NUM[cn[2]]) {
    // "X十Y" → X*10 + Y (21-99)
    num = CN_NUM[cn[0]] * 10 + CN_NUM[cn[2]]
  } else if (cn.length === 1) {
    num = CN_NUM[cn] || 999
  } else {
    num = 999
  }
  return num
}

function sortChapters(chapters: string[]): string[] {
  return [...chapters].sort((a, b) => parseChapterNumber(a) - parseChapterNumber(b))
}

function sortChapterEntries<K>(entries: [string, K][]): [string, K][] {
  return [...entries].sort((a, b) => parseChapterNumber(a[0]) - parseChapterNumber(b[0]))
}

// ====== Tests ======

describe('parseChapterNumber', () => {
  it('should parse simple chapters', () => {
    expect(parseChapterNumber('第一章 函数极限')).toBe(1)
    expect(parseChapterNumber('第二章 导数')).toBe(2)
    expect(parseChapterNumber('第三章 积分')).toBe(3)
    expect(parseChapterNumber('第十章 反常积分')).toBe(10)
  })

  it('should parse compound chapters (11-20)', () => {
    expect(parseChapterNumber('第十一章')).toBe(11)
    expect(parseChapterNumber('第十二章')).toBe(12)
    expect(parseChapterNumber('第十五章')).toBe(15)
    expect(parseChapterNumber('第二十章')).toBe(20)
  })

  it('should parse chapters like 二十X', () => {
    expect(parseChapterNumber('第二十一章')).toBe(21)
    expect(parseChapterNumber('第二十五章')).toBe(25)
    expect(parseChapterNumber('第九十九章')).toBe(99)
  })

  it('should handle chapters like 三十, 四十', () => {
    expect(parseChapterNumber('第三十章')).toBe(30)
    expect(parseChapterNumber('第四十章')).toBe(40)
  })

  it('should return 999 for non-matching strings', () => {
    expect(parseChapterNumber('附录')).toBe(999)
    expect(parseChapterNumber('')).toBe(999)
    expect(parseChapterNumber('AI 生成')).toBe(999)
  })

  it('should handle edge case: empty suffix after 第X章', () => {
    expect(parseChapterNumber('第一章 函数与极限')).toBe(1)
    expect(parseChapterNumber('第二章')).toBe(2)
  })
})

describe('sortChapters', () => {
  it('should sort chapters by Chinese number', () => {
    const input = ['第三章', '第一章', '第十章', '第二章']
    const sorted = sortChapters(input)
    expect(sorted).toEqual(['第一章', '第二章', '第三章', '第十章'])
  })

  it('should handle mixed singe/double digit', () => {
    const input = ['第十一章', '第一章', '第二十章', '第二章']
    const sorted = sortChapters(input)
    expect(sorted).toEqual(['第一章', '第二章', '第十一章', '第二十章'])
  })

  it('should push unknown chapters to the end', () => {
    const input = ['AI 生成', '第一章', '附录', '第二章']
    const sorted = sortChapters(input)
    expect(sorted[0]).toBe('第一章')
    expect(sorted[1]).toBe('第二章')
    // Unknown chapters at end
    expect(sorted.slice(2)).toContain('AI 生成')
    expect(sorted.slice(2)).toContain('附录')
  })

  it('should handle empty array', () => {
    expect(sortChapters([])).toEqual([])
  })

  it('should handle single element', () => {
    expect(sortChapters(['第一章'])).toEqual(['第一章'])
  })
})

describe('sortChapterEntries', () => {
  it('should sort entries by chapter key', () => {
    const input: [string, number[]][] = [
      ['第三章', [1, 2]],
      ['第一章', [3, 4]],
      ['第二章', [5]],
    ]
    const sorted = sortChapterEntries(input)
    expect(sorted[0][0]).toBe('第一章')
    expect(sorted[1][0]).toBe('第二章')
    expect(sorted[2][0]).toBe('第三章')
    // Values should follow their chapters
    expect(sorted[0][1]).toEqual([3, 4])
    expect(sorted[2][1]).toEqual([1, 2])
  })
})
