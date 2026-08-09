import { Router, Request, Response } from 'express'
import bcrypt from 'bcrypt'
import crypto from 'node:crypto'
import { v4 as uuid } from 'uuid'
import { eq, or, and } from 'drizzle-orm'
import { getDrizzle } from '../db/index.js'
import { users, refreshTokens, workbooks } from '../db/schema.js'
import { registerSchema, loginSchema, refreshSchema } from '../lib/schema.js'
import { signAccessToken, generateRefreshToken, refreshTokenExpiry } from '../lib/jwt.js'
import { authRequired } from '../middleware/auth.js'
import { ZodError } from 'zod'

const router = Router()

function zodErrorFirst(err: ZodError): string {
  return err.issues[0]?.message ?? '请求参数校验失败'
}

// POST /api/auth/register
router.post('/register', async (req: Request, res: Response) => {
  try {
    const { username, email, password } = registerSchema.parse(req.body)

    const db = getDrizzle()

    const existing = db
      .select({ id: users.id })
      .from(users)
      .where(or(eq(users.email, email), eq(users.username, username)))
      .get()

    if (existing) {
      return res.status(409).json({ error: '用户名或邮箱已被注册' })
    }

    const id = uuid()
    const passwordHash = await bcrypt.hash(password, 12)
    const now = new Date().toISOString()

    db.insert(users).values({
      id,
      username,
      email,
      password_hash: passwordHash,
      created_at: now,
    }).run()

    const accessToken = signAccessToken({ userId: id, username })
    const newRefreshToken = generateRefreshToken()
    const refreshHash = crypto.createHash('sha256').update(newRefreshToken).digest('hex')

    db.insert(refreshTokens).values({
      id: uuid(),
      user_id: id,
      token_hash: refreshHash,
      expires_at: refreshTokenExpiry(),
    }).run()

    // Ensure default workbook exists
    const wbExists = db
      .select({ id: workbooks.id })
      .from(workbooks)
      .where(and(eq(workbooks.user_id, id), eq(workbooks.id, 'default')))
      .get()

    if (!wbExists) {
      db.insert(workbooks).values({
        id: 'default',
        user_id: id,
        name: '默认练习册',
        description: '默认练习册',
        created_at: now,
      }).run()
    }

    return res.status(201).json({
      user: { id, username, email },
      accessToken,
      refreshToken: newRefreshToken,
    })
  } catch (err: any) {
    if (err instanceof ZodError) {
      return res.status(400).json({ error: zodErrorFirst(err) })
    }
    console.error('Register error:', err)
    return res.status(500).json({ error: '注册失败' })
  }
})

// POST /api/auth/login
router.post('/login', async (req: Request, res: Response) => {
  try {
    const { email, password } = loginSchema.parse(req.body)

    const db = getDrizzle()

    const user = db
      .select({
        id: users.id,
        username: users.username,
        email: users.email,
        password_hash: users.password_hash,
      })
      .from(users)
      .where(eq(users.email, email))
      .get()

    if (!user) {
      return res.status(401).json({ error: '邮箱或密码错误' })
    }

    const valid = await bcrypt.compare(password, user.password_hash)
    if (!valid) {
      return res.status(401).json({ error: '邮箱或密码错误' })
    }

    const accessToken = signAccessToken({ userId: user.id, username: user.username })
    const newRefreshToken = generateRefreshToken()
    const refreshHash = crypto.createHash('sha256').update(newRefreshToken).digest('hex')

    db.insert(refreshTokens).values({
      id: uuid(),
      user_id: user.id,
      token_hash: refreshHash,
      expires_at: refreshTokenExpiry(),
    }).run()

    // Ensure default workbook
    const now = new Date().toISOString()
    const wbExists = db
      .select({ id: workbooks.id })
      .from(workbooks)
      .where(and(eq(workbooks.user_id, user.id), eq(workbooks.id, 'default')))
      .get()

    if (!wbExists) {
      db.insert(workbooks).values({
        id: 'default',
        user_id: user.id,
        name: '默认练习册',
        description: '默认练习册',
        created_at: now,
      }).run()
    }

    return res.json({
      user: { id: user.id, username: user.username, email: user.email },
      accessToken,
      refreshToken: newRefreshToken,
    })
  } catch (err: any) {
    if (err instanceof ZodError) {
      return res.status(400).json({ error: zodErrorFirst(err) })
    }
    console.error('Login error:', err)
    return res.status(500).json({ error: '登录失败' })
  }
})

// POST /api/auth/refresh
router.post('/refresh', (req: Request, res: Response) => {
  try {
    const { refreshToken } = refreshSchema.parse(req.body)

    const db = getDrizzle()
    const refreshHash = crypto.createHash('sha256').update(refreshToken).digest('hex')

    const row = db
      .select({
        user_id: refreshTokens.user_id,
        expires_at: refreshTokens.expires_at,
        username: users.username,
      })
      .from(refreshTokens)
      .innerJoin(users, eq(users.id, refreshTokens.user_id))
      .where(eq(refreshTokens.token_hash, refreshHash))
      .get()

    if (!row) {
      return res.status(401).json({ error: '无效的 refresh token' })
    }
    if (new Date(row.expires_at) < new Date()) {
      db.delete(refreshTokens).where(eq(refreshTokens.token_hash, refreshHash)).run()
      return res.status(401).json({ error: 'refresh token 已过期，请重新登录' })
    }

    // Rotate: delete old, issue new
    db.delete(refreshTokens).where(eq(refreshTokens.token_hash, refreshHash)).run()

    const newAccessToken = signAccessToken({ userId: row.user_id, username: row.username })
    const newRefreshToken = generateRefreshToken()
    const newHash = crypto.createHash('sha256').update(newRefreshToken).digest('hex')

    db.insert(refreshTokens).values({
      id: uuid(),
      user_id: row.user_id,
      token_hash: newHash,
      expires_at: refreshTokenExpiry(),
    }).run()

    return res.json({ accessToken: newAccessToken, refreshToken: newRefreshToken })
  } catch (err: any) {
    if (err instanceof ZodError) {
      return res.status(400).json({ error: zodErrorFirst(err) })
    }
    console.error('Refresh error:', err)
    return res.status(500).json({ error: '刷新失败' })
  }
})

// POST /api/auth/logout
router.post('/logout', authRequired, (req: Request, res: Response) => {
  const { refreshToken } = req.body
  if (refreshToken) {
    const db = getDrizzle()
    const refreshHash = crypto.createHash('sha256').update(refreshToken).digest('hex')
    db
      .delete(refreshTokens)
      .where(and(eq(refreshTokens.token_hash, refreshHash), eq(refreshTokens.user_id, req.userId!)))
      .run()
  }
  return res.json({ ok: true })
})

// GET /api/auth/me
router.get('/me', authRequired, (req: Request, res: Response) => {
  const db = getDrizzle()
  const user = db
    .select({
      id: users.id,
      username: users.username,
      email: users.email,
      created_at: users.created_at,
    })
    .from(users)
    .where(eq(users.id, req.userId!))
    .get()

  if (!user) return res.status(404).json({ error: '用户不存在' })
  return res.json({ user })
})

export default router
