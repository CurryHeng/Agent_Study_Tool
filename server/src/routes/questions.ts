import { Router, Request, Response } from 'express'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { eq, desc, and } from 'drizzle-orm'
import { getDrizzle } from '../db/index.js'
import { questions, cards, wrongRecords } from '../db/schema.js'
import { createQuestionSchema, updateQuestionSchema } from '../lib/schema.js'
import { authRequired } from '../middleware/auth.js'
import { ZodError } from 'zod'

const router = Router()
router.use(authRequired)

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const builtInPath = path.join(__dirname, '..', '..', 'data', 'questions.json')

function loadBuiltInQuestions(): any[] {
  try {
    if (fs.existsSync(builtInPath)) {
      return JSON.parse(fs.readFileSync(builtInPath, 'utf-8'))
    }
  } catch { /* missing file */ }
  return []
}

function zodErrorFirst(err: ZodError): string {
  return err.issues[0]?.message ?? '请求参数校验失败'
}

// GET /api/questions — returns built-in + user questions
router.get('/', (req: Request, res: Response) => {
  try {
    const db = getDrizzle()
    const userQuestions = db
      .select()
      .from(questions)
      .where(eq(questions.user_id, req.userId!))
      .orderBy(desc(questions.created_at))
      .all()

    return res.json([...loadBuiltInQuestions(), ...userQuestions])
  } catch (err: any) {
    console.error('GET /questions error:', err)
    return res.status(500).json({ error: '获取题目失败' })
  }
})

// POST /api/questions
router.post('/', (req: Request, res: Response) => {
  try {
    const data = createQuestionSchema.parse(req.body)
    const id = data.id || ('user-' + Date.now())
    const now = new Date().toISOString()

    const db = getDrizzle()
    db.insert(questions).values({
      id,
      user_id: req.userId!,
      chapter: data.chapter,
      question_number: data.questionNumber || '?',
      original_number: data.originalNumber || '-',
      problem: data.problem,
      image: data.image ?? null,
      wrong_answer: data.wrongAnswer || '',
      wrong_reason: data.wrongReason || '',
      correct_answer: data.correctAnswer || '',
      steps: data.steps || '',
      summary: data.summary || '',
      knowledge_points: JSON.stringify(data.knowledgePoints || []),
      workbook_id: data.workbookId || 'default',
      created_at: now,
      updated_at: now,
    }).run()

    return res.status(201).json({ id, updatedAt: now })
  } catch (err: any) {
    if (err instanceof ZodError) {
      return res.status(400).json({ error: zodErrorFirst(err) })
    }
    console.error('POST /questions error:', err)
    return res.status(500).json({ error: '添加题目失败' })
  }
})

// PUT /api/questions/:id
router.put('/:id', (req: Request, res: Response) => {
  try {
    const db = getDrizzle()
    const qid = req.params.id as string

    const existing = db
      .select({ id: questions.id, user_id: questions.user_id })
      .from(questions)
      .where(eq(questions.id, qid))
      .get()

    if (!existing) return res.status(404).json({ error: '题目不存在' })
    if (existing.user_id !== req.userId!) return res.status(403).json({ error: '无权修改此题目' })

    const fields = updateQuestionSchema.parse(req.body)
    const now = new Date().toISOString()

    const setData: Record<string, any> = { updated_at: now }

    if (fields.chapter !== undefined) setData.chapter = fields.chapter
    if (fields.questionNumber !== undefined) setData.question_number = fields.questionNumber
    if (fields.originalNumber !== undefined) setData.original_number = fields.originalNumber
    if (fields.problem !== undefined) setData.problem = fields.problem
    if (fields.image !== undefined) setData.image = fields.image
    if (fields.wrongAnswer !== undefined) setData.wrong_answer = fields.wrongAnswer
    if (fields.wrongReason !== undefined) setData.wrong_reason = fields.wrongReason
    if (fields.correctAnswer !== undefined) setData.correct_answer = fields.correctAnswer
    if (fields.steps !== undefined) setData.steps = fields.steps
    if (fields.summary !== undefined) setData.summary = fields.summary
    if (fields.knowledgePoints !== undefined) setData.knowledge_points = JSON.stringify(fields.knowledgePoints)
    if (fields.workbookId !== undefined) setData.workbook_id = fields.workbookId

    db.update(questions).set(setData).where(eq(questions.id, qid)).run()

    return res.json({ updatedAt: now })
  } catch (err: any) {
    if (err instanceof ZodError) {
      return res.status(400).json({ error: zodErrorFirst(err) })
    }
    console.error('PUT /questions error:', err)
    return res.status(500).json({ error: '更新题目失败' })
  }
})

// DELETE /api/questions/:id
router.delete('/:id', (req: Request, res: Response) => {
  try {
    const db = getDrizzle()
    const qid = req.params.id as string

    const existing = db
      .select({ id: questions.id, user_id: questions.user_id })
      .from(questions)
      .where(eq(questions.id, qid))
      .get()

    if (!existing) return res.status(404).json({ error: '题目不存在' })
    if (existing.user_id !== req.userId!) return res.status(403).json({ error: '无权删除此题目' })

    db.delete(wrongRecords)
      .where(and(eq(wrongRecords.question_id, qid), eq(wrongRecords.user_id, req.userId!)))
      .run()
    db.delete(cards)
      .where(and(eq(cards.question_id, qid), eq(cards.user_id, req.userId!)))
      .run()
    db.delete(questions).where(eq(questions.id, qid)).run()

    return res.json({ ok: true })
  } catch (err: any) {
    console.error('DELETE /questions error:', err)
    return res.status(500).json({ error: '删除题目失败' })
  }
})

export default router
