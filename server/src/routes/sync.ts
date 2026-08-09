import { Router, Request, Response } from 'express'
import { getDb } from '../db.js'
import { authRequired } from '../middleware/auth.js'

const router = Router()
router.use(authRequired)

// POST /api/sync — full sync: receive client data, return merged server data
router.post('/', (req: Request, res: Response) => {
  try {
    const db = getDb()
    const userId = req.userId!
    const { clientData } = req.body || {}
    const now = new Date().toISOString()

    const changes = { questions: 0, cards: 0, logs: 0, workbooks: 0 }

    // --- Merge questions ---
    if (clientData?.questions && Array.isArray(clientData.questions)) {
      const insertQ = db.prepare(`INSERT OR REPLACE INTO questions (
        id, user_id, chapter, question_number, original_number, problem,
        image, wrong_answer, wrong_reason, correct_answer, steps, summary,
        knowledge_points, workbook_id, created_at, updated_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`)

      const mergeQuestions = db.transaction((qs: any[]) => {
        for (const q of qs) {
          if (!q.id || !q.id.startsWith('user-')) continue // only user questions
          insertQ.run(
            q.id, userId, q.chapter || '', q.questionNumber || '?',
            q.originalNumber || '-', q.problem || '',
            q.image || null, q.wrongAnswer || '', q.wrongReason || '',
            q.correctAnswer || '', q.steps || '', q.summary || '',
            JSON.stringify(q.knowledgePoints || []),
            q.workbookId || 'default',
            q.createdAt || now, q.updatedAt || now,
          )
        }
      })
      mergeQuestions(clientData.questions)
      changes.questions = clientData.questions.filter((q: any) => q.id?.startsWith('user-')).length
    }

    // --- Merge cards ---
    if (clientData?.cards && Array.isArray(clientData.cards)) {
      const insertC = db.prepare(`INSERT OR REPLACE INTO cards (
        question_id, user_id, ease, "interval", repetitions,
        next_review, last_review, total_attempts, total_correct, favorited
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`)

      const mergeCards = db.transaction((cs: any[]) => {
        for (const c of cs) {
          if (!c.questionId) continue
          insertC.run(
            c.questionId, userId,
            c.ease ?? 2.5, c.interval ?? 0, c.repetitions ?? 0,
            c.nextReview || now.split('T')[0], c.lastReview || null,
            c.totalAttempts ?? 0, c.totalCorrect ?? 0,
            c.favorited ? 1 : 0,
          )
        }
      })
      mergeCards(clientData.cards)
      changes.cards = clientData.cards.length
    }

    // --- Merge logs ---
    if (clientData?.logs && Array.isArray(clientData.logs)) {
      const insertL = db.prepare(`INSERT OR IGNORE INTO review_logs (
        id, user_id, question_id, rating, date, mode, choice_selected, choice_correct, time_spent
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`)

      const mergeLogs = db.transaction((ls: any[]) => {
        for (const l of ls) {
          if (!l.id || !l.questionId) continue
          insertL.run(
            l.id, userId, l.questionId, l.rating, l.date || now,
            l.mode || null, l.choiceSelected || null,
            l.choiceCorrect === undefined ? null : (l.choiceCorrect ? 1 : 0),
            l.timeSpent || null,
          )
        }
      })
      mergeLogs(clientData.logs)
      changes.logs = clientData.logs.length
    }

    // --- Merge workbooks ---
    if (clientData?.workbooks && Array.isArray(clientData.workbooks)) {
      const insertW = db.prepare('INSERT OR REPLACE INTO workbooks (id, user_id, name, description, created_at) VALUES (?, ?, ?, ?, ?)')

      const mergeWbs = db.transaction((ws: any[]) => {
        for (const w of ws) {
          if (!w.id || w.id === 'default') continue
          insertW.run(w.id, userId, w.name || '', w.description || '', w.createdAt || now)
        }
      })
      mergeWbs(clientData.workbooks)
      changes.workbooks = clientData.workbooks.filter((w: any) => w.id !== 'default').length
    }

    // --- Return full server state ---
    const serverQuestions = db.prepare(
      'SELECT * FROM questions WHERE user_id = ?'
    ).all(userId) as any[]

    const serverCards = db.prepare(
      'SELECT * FROM cards WHERE user_id = ?'
    ).all(userId) as any[]

    const serverLogs = db.prepare(
      'SELECT * FROM review_logs WHERE user_id = ?'
    ).all(userId) as any[]

    const serverWorkbooks = db.prepare(
      'SELECT * FROM workbooks WHERE user_id = ?'
    ).all(userId) as any[]

    return res.json({
      syncedAt: now,
      changes,
      data: {
        questions: serverQuestions,
        cards: serverCards,
        logs: serverLogs,
        workbooks: serverWorkbooks,
      },
    })
  } catch (err: any) {
    console.error('POST /sync error:', err)
    return res.status(500).json({ error: '同步失败' })
  }
})

export default router
