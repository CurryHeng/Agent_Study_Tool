import { describe, expect, it } from 'vitest'
import { gradeQuestion } from '../lib/grading'
import type { Question, QuestionType } from '../types'

function q(type: QuestionType, answer: string): Question {
  return {
    id: 1,
    workbook_id: 0,
    knowledge_id: null,
    type,
    content: 'c',
    answer,
    analysis: null,
    summary: null,
    image: null,
    difficulty: 1,
    source: 'builtin',
    status: 'approved',
    original_number: null,
    question_number: null,
    knowledge_name: null,
    created_at: '',
    updated_at: '',
    options: [],
  }
}

describe('前端判题 grading', () => {
  it('single_choice 大小写不敏感', () => {
    expect(gradeQuestion(q('single_choice', 'B'), 'B')).toBe(true)
    expect(gradeQuestion(q('single_choice', 'B'), 'b')).toBe(true)
    expect(gradeQuestion(q('single_choice', 'B'), 'A')).toBe(false)
  })

  it('multiple_choice 集合相等', () => {
    expect(gradeQuestion(q('multiple_choice', 'ABD'), 'DBA')).toBe(true)
    expect(gradeQuestion(q('multiple_choice', 'ABD'), 'AB')).toBe(false)
  })

  it('true_false 归一化', () => {
    expect(gradeQuestion(q('true_false', 'true'), '正确')).toBe(true)
    expect(gradeQuestion(q('true_false', 'true'), 'false')).toBe(false)
  })

  it('fill_blank 去空格小写', () => {
    expect(gradeQuestion(q('fill_blank', '数据'), ' 数据 ')).toBe(true)
    expect(gradeQuestion(q('fill_blank', '数据'), '模型')).toBe(false)
  })
})
