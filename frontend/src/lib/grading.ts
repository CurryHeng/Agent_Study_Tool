import type { Question, QuestionType } from '../types'

const AUTO_TYPES: QuestionType[] = [
  'single_choice',
  'multiple_choice',
  'true_false',
  'fill_blank',
]

export function isAutoGradable(type: QuestionType): boolean {
  return AUTO_TYPES.includes(type)
}

function normalizeBool(v: string): string {
  const t = v.toLowerCase()
  if (['true', 't', '1', '正确', '对', '是', 'yes', 'y'].includes(t)) return 'true'
  if (['false', 'f', '0', '错误', '错', '否', 'no', 'n'].includes(t)) return 'false'
  return t
}

/** 前端本地判题（与后端 grading.py 保持一致，用于即时反馈） */
export function gradeQuestion(question: Question, userAnswer: string | null): boolean {
  const a = (question.answer || '').trim()
  const u = (userAnswer || '').trim()
  switch (question.type) {
    case 'single_choice':
      return u.toUpperCase() === a.toUpperCase()
    case 'multiple_choice':
      return [...u.toUpperCase()].sort().join('') === [...a.toUpperCase()].sort().join('')
    case 'true_false':
      return normalizeBool(u) === normalizeBool(a)
    case 'fill_blank':
      return u.toLowerCase() === a.toLowerCase()
    default:
      return false
  }
}
