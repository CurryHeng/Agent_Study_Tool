import { z } from 'zod'

// ── 注册请求体 ────────────────────────────────────────────────────────
export const registerSchema = z.object({
  username: z.string().min(1, '用户名不能为空'),
  email: z.string().min(1, '邮箱不能为空').email('邮箱格式不正确'),
  password: z.string().min(8, '密码至少 8 个字符'),
})

// ── 登录请求体 ────────────────────────────────────────────────────────
export const loginSchema = z.object({
  email: z.string().min(1, '邮箱不能为空'),
  password: z.string().min(1, '密码不能为空'),
})

// ── 刷新 token 请求体 ─────────────────────────────────────────────────
export const refreshSchema = z.object({
  refreshToken: z.string().min(1, 'refreshToken 不能为空'),
})

// ── 创建题目请求体 ────────────────────────────────────────────────────
export const createQuestionSchema = z.object({
  id: z.string().optional(),
  chapter: z.string().min(1, '章节不能为空'),
  questionNumber: z.string().optional(),
  originalNumber: z.string().optional(),
  problem: z.string().min(1, '题目内容不能为空'),
  image: z.string().nullable().optional(),
  wrongAnswer: z.string().optional(),
  wrongReason: z.string().optional(),
  correctAnswer: z.string().optional(),
  steps: z.string().optional(),
  summary: z.string().optional(),
  knowledgePoints: z.array(z.string()).optional(),
  workbookId: z.string().optional(),
})

// ── 更新题目请求体 ────────────────────────────────────────────────────
export const updateQuestionSchema = createQuestionSchema.partial()
