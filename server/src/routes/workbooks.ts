import { Router, Request, Response } from 'express'
import { v4 as uuid } from 'uuid'
import { getDb } from '../db.js'
import { authRequired } from '../middleware/auth.js'

const router = Router()
router.use(authRequired)

const DEFAULT_WORKBOOK = {
  id: 'default',
  name: '默认练习册',
  description: '默认练习册',
}

// GET /api/workbooks
router.get('/', (req: Request, res: Response) => {
  try {
    const db = getDb()
    const rows = db.prepare(
      'SELECT id, name, description, created_at FROM workbooks WHERE user_id = ? ORDER BY created_at ASC'
    ).all(req.userId!) as any[]

    // Ensure default workbook always exists
    const hasDefault = rows.some((r: any) => r.id === 'default')
    if (!hasDefault) {
      const now = new Date().toISOString()
      db.prepare('INSERT INTO workbooks (id, user_id, name, description, created_at) VALUES (?, ?, ?, ?, ?)')
        .run('default', req.userId!, DEFAULT_WORKBOOK.name, DEFAULT_WORKBOOK.description, now)
      rows.unshift({ id: 'default', name: DEFAULT_WORKBOOK.name, description: DEFAULT_WORKBOOK.description, created_at: now })
    }

    // Attach question counts
    const counts = db.prepare(
      'SELECT workbook_id, COUNT(*) as count FROM questions WHERE user_id = ? GROUP BY workbook_id'
    ).all(req.userId!) as any[]

    const countMap = new Map(counts.map((c: any) => [c.workbook_id, c.count]))
    const result = rows.map((r: any) => ({
      ...r,
      questionCount: countMap.get(r.id) || 0,
    }))

    return res.json(result)
  } catch (err: any) {
    console.error('GET /workbooks error:', err)
    return res.status(500).json({ error: '获取练习册失败' })
  }
})

// POST /api/workbooks
router.post('/', (req: Request, res: Response) => {
  try {
    const { name, description } = req.body
    if (!name || !name.trim()) {
      return res.status(400).json({ error: '练习册名称不能为空' })
    }

    const db = getDb()
    const id = 'wb-' + Date.now()
    const now = new Date().toISOString()

    db.prepare('INSERT INTO workbooks (id, user_id, name, description, created_at) VALUES (?, ?, ?, ?, ?)')
      .run(id, req.userId!, name.trim(), description || '', now)

    return res.status(201).json({ id, name: name.trim(), description: description || '', created_at: now, questionCount: 0 })
  } catch (err: any) {
    console.error('POST /workbooks error:', err)
    return res.status(500).json({ error: '创建练习册失败' })
  }
})

export default router
