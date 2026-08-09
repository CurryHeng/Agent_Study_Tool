import { z } from 'zod'

// ====== 选择题选项 ======
export const ChoiceSchema = z.object({
  letter: z.string(),
  text: z.string(),
})
export type Choice = z.infer<typeof ChoiceSchema>

// Use `label` field (from questions.json) or fall back to `letter`
export const ChoiceInputSchema = z.object({
  label: z.string().optional(),
  letter: z.string().optional(),
  text: z.string(),
})

// ====== 练习册 ======
export const WorkbookSchema = z.object({
  id: z.string(),
  name: z.string().min(1, '练习册名称不能为空'),
  description: z.string().optional(),
  createdAt: z.string(),
})
export type Workbook = z.infer<typeof WorkbookSchema>

// ====== 题目 ======
export const QuestionSchema = z.object({
  id: z.string(),
  chapter: z.string().min(1, '章节不能为空'),
  questionNumber: z.string(),
  originalNumber: z.string(),
  problem: z.string().min(1, '题目内容不能为空'),
  image: z.string().optional(),
  wrongAnswer: z.string().optional().default(''),
  wrongReason: z.string().optional().default(''),
  correctAnswer: z.string().default(''),
  steps: z.string().default(''),
  summary: z.string().default(''),
  knowledgePoints: z.array(z.string()).default([]),
  workbookId: z.string().optional(),
  choices: z.array(ChoiceInputSchema).optional(),
})
export type Question = z.infer<typeof QuestionSchema>

// ====== 错误记录 ======
export const WrongRecordSchema = z.object({
  date: z.string(),
  wrongAnswer: z.string().default(''),
  wrongReason: z.string().default(''),
})
export type WrongRecord = z.infer<typeof WrongRecordSchema>

// ====== 复习卡片 ======
export const ReviewCardSchema = z.object({
  questionId: z.string(),
  ease: z.number().default(2.5),
  interval: z.number().default(0),
  repetitions: z.number().default(0),
  nextReview: z.string(),
  lastReview: z.string().nullable(),
  totalAttempts: z.number().default(0),
  totalCorrect: z.number().default(0),
  favorited: z.boolean().default(false),
  wrongRecords: z.array(WrongRecordSchema).default([]),
})
export type ReviewCard = z.infer<typeof ReviewCardSchema>

// ====== 评分 ======
export const RatingEnum = z.enum(['again', 'hard', 'good', 'easy'])
export type Rating = z.infer<typeof RatingEnum>

// ====== 复习日志 ======
export const ReviewLogSchema = z.object({
  questionId: z.string(),
  rating: RatingEnum,
  date: z.string(),
  mode: z.enum(['relaxed', 'normal', 'strict']).optional(),
  choiceSelected: z.string().optional(),
  choiceCorrect: z.boolean().optional(),
  timeSpent: z.number().optional(),
})
export type ReviewLog = z.infer<typeof ReviewLogSchema>

// ====== 练习模式 ======
export type QuizMode = 'relaxed' | 'normal' | 'strict'

// ====== 章节排序中文数字映射 ======
export const CN_NUM: Record<string, number> = {
  '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
  '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
}
export const CN_NUM_REV: Record<string, number> = {
  '十一': 11, '十二': 12, '十三': 13, '十四': 14, '十五': 15,
  '十六': 16, '十七': 17, '十八': 18, '十九': 19, '二十': 20,
}

export function parseChapterNumber(chapter: string): number {
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
    num = CN_NUM[cn[0]] * 10 + CN_NUM[cn[2]]
  } else if (cn.length === 1) {
    num = CN_NUM[cn] || 999
  } else {
    num = 999
  }
  return num
}
