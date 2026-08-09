// 共享类型和校验规则 — 前后端统一从这一个文件引入

export {
  WorkbookSchema,
  QuestionSchema,
  WrongRecordSchema,
  ReviewCardSchema,
  RatingEnum,
  ReviewLogSchema,
  ChoiceSchema,
  CN_NUM,
  CN_NUM_REV,
  parseChapterNumber,
} from '../../../src/lib/schema'

export type {
  Workbook,
  Question,
  WrongRecord,
  ReviewCard,
  Rating,
  ReviewLog,
  Choice,
  QuizMode,
} from '../../../src/lib/schema'

// 后端请求校验 schema（仅后端用）
export const registerSchema = null // 由 server/src/lib/schema.ts 定义
export const loginSchema = null
export const createQuestionSchema = null
export const updateQuestionSchema = null
