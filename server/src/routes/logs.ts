import { Router, Request, Response } from 'express'
import { v4 as uuid } from 'uuid'
import { getDb } from '../db.js'
import { authRequired } from '../middleware/auth.js'

const router = Router()
router.use(authRequired)

// GET /api/logs
router.get('/', (req: Request, res: Response) => {
  try {
    const db = getDb()
    const since = req.query.since as string | undefined

    let rows
    if (since) {
      rows = db.prepare(
        'SELECT * FROM review_logs WHERE user_id = ? AND date >= ? ORDER BY date DESC'
      ).all(req.userId!, since) as any[]
    } else {
      rows = db.prepare(
        'SELECT * FROM review_logs WHERE user_id = ? ORDER BY date DESC'
      ).all(req.userId!) as any[]
    }

    return res.json(rows)
  } catch (err: any) {
    console.error('GET /logs error:', err)
    return res.status(500).json({ error: '获取日志失败' })
  }
})

// POST /api/logs
router.post('/', (req: Request, res: Response) => {
  try {
    const db = getDb()
    const logs = Array.isArray(req.body) ? req.body : [req.body]

    const insert = db.prepare(`INSERT INTO review_logs
      (id, user_id, question_id, rating, date, mode, choice_selected, choice_correct, time_spent)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`)

    const now = new Date().toISOString()
    const runMany = db.transaction((entries: any[]) => {
      for (const entry of entries) {
        insert.run(
          entry.id || uuid(),
          req.userId!,
          entry.questionId,
          entry.rating,
          entry.date || now,
          entry.mode || null,
          entry.choiceSelected || null,
          entry.choiceCorrect === undefined ? null : (entry.choiceCorrect ? 1 : 0),
          entry.timeSpent || null,
        )
      }
    })

    runMany(logs)

    return res.status(201).json({ count: logs.length })
  } catch (err: any) {
    console.error('POST /logs error:', err)
    return res.status(500).json({ error: '保存日志失败' })
  }
})

export default router
