import { Router, Request, Response } from 'express'
import { getDb } from '../db.js'
import { authRequired } from '../middleware/auth.js'
import { createCardData, reviewCardData } from '../lib/sm2.js'

const router = Router()
router.use(authRequired)

// GET /api/cards
router.get('/', (req: Request, res: Response) => {
  try {
    const db = getDb()
    const cards = db.prepare(
      'SELECT * FROM cards WHERE user_id = ?'
    ).all(req.userId!) as any[]
    return res.json(cards)
  } catch (err: any) {
    console.error('GET /cards error:', err)
    return res.status(500).json({ error: '获取卡片失败' })
  }
})

// PUT /api/cards/:questionId
router.put('/:questionId', (req: Request, res: Response) => {
  try {
    const db = getDb()
    const qid = req.params.questionId as string

    let card = db.prepare(
      'SELECT * FROM cards WHERE question_id = ? AND user_id = ?'
    ).get(qid, req.userId!) as any

    if (!card) {
      // Auto-create card if it doesn't exist
      const defaultCard = createCardData(qid)
      db.prepare(`INSERT INTO cards (question_id, user_id, ease, "interval", repetitions, next_review, last_review, total_attempts, total_correct, favorited)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(
        qid, req.userId!, defaultCard.ease, defaultCard.interval, defaultCard.repetitions,
        defaultCard.nextReview, defaultCard.lastReview, defaultCard.totalAttempts,
        defaultCard.totalCorrect, defaultCard.favorited ? 1 : 0,
      )
      card = db.prepare('SELECT * FROM cards WHERE question_id = ? AND user_id = ?').get(qid, req.userId!) as any
    }

    const fields = req.body
    if (fields.rating) {
      // Apply SM-2 review
      const updated = reviewCardData(card, fields.rating, fields.isCorrect)
      db.prepare(`UPDATE cards SET ease = ?, "interval" = ?, repetitions = ?, next_review = ?,
        last_review = ?, total_attempts = ?, total_correct = ?
        WHERE question_id = ? AND user_id = ?`).run(
        updated.ease, updated.interval, updated.repetitions, updated.nextReview,
        updated.lastReview, updated.totalAttempts, updated.totalCorrect,
        qid, req.userId!,
      )
    } else {
      // Generic update
      const sets: string[] = []
      const values: any[] = []
      if (fields.ease !== undefined) { sets.push('ease = ?'); values.push(fields.ease) }
      if (fields.interval !== undefined) { sets.push('"interval" = ?'); values.push(fields.interval) }
      if (fields.repetitions !== undefined) { sets.push('repetitions = ?'); values.push(fields.repetitions) }
      if (fields.nextReview !== undefined) { sets.push('next_review = ?'); values.push(fields.nextReview) }
      if (fields.lastReview !== undefined) { sets.push('last_review = ?'); values.push(fields.lastReview) }
      if (fields.totalAttempts !== undefined) { sets.push('total_attempts = ?'); values.push(fields.totalAttempts) }
      if (fields.totalCorrect !== undefined) { sets.push('total_correct = ?'); values.push(fields.totalCorrect) }
      if (fields.favorited !== undefined) { sets.push('favorited = ?'); values.push(fields.favorited ? 1 : 0) }
      if (sets.length > 0) {
        values.push(qid, req.userId!)
        db.prepare(`UPDATE cards SET ${sets.join(', ')} WHERE question_id = ? AND user_id = ?`).run(...values)
      }
    }

    const updated = db.prepare('SELECT * FROM cards WHERE question_id = ? AND user_id = ?').get(qid, req.userId!)
    return res.json(updated)
  } catch (err: any) {
    console.error('PUT /cards error:', err)
    return res.status(500).json({ error: '更新卡片失败' })
  }
})

// PUT /api/cards/:questionId/favorite
router.put('/:questionId/favorite', (req: Request, res: Response) => {
  try {
    const db = getDb()
    const qid = req.params.questionId as string

    let card = db.prepare(
      'SELECT * FROM cards WHERE question_id = ? AND user_id = ?'
    ).get(qid, req.userId!) as any

    if (!card) {
      const defaultCard = createCardData(qid)
      db.prepare(`INSERT INTO cards (question_id, user_id, ease, "interval", repetitions, next_review, last_review, total_attempts, total_correct, favorited)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(
        qid, req.userId!, defaultCard.ease, defaultCard.interval, defaultCard.repetitions,
        defaultCard.nextReview, defaultCard.lastReview, defaultCard.totalAttempts,
        defaultCard.totalCorrect, 1,
      )
      return res.json({ favorited: true })
    }

    const newFav = card.favorited ? 0 : 1
    db.prepare('UPDATE cards SET favorited = ? WHERE question_id = ? AND user_id = ?').run(newFav, qid, req.userId!)
    return res.json({ favorited: !!newFav })
  } catch (err: any) {
    console.error('PUT /cards/favorite error:', err)
    return res.status(500).json({ error: '收藏操作失败' })
  }
})

export default router
