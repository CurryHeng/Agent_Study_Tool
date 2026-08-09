import { Request, Response, NextFunction } from 'express'
import { verifyAccessToken, TokenPayload } from '../lib/jwt.js'

declare global {
  namespace Express {
    interface Request {
      userId?: string
      username?: string
    }
  }
}

export function authRequired(req: Request, res: Response, next: NextFunction) {
  const header = req.headers.authorization
  if (!header || !header.startsWith('Bearer ')) {
    return res.status(401).json({ error: '未登录，请先登录' })
  }

  const token = header.slice(7)
  try {
    const payload: TokenPayload = verifyAccessToken(token)
    req.userId = payload.userId
    req.username = payload.username
    next()
  } catch {
    return res.status(401).json({ error: 'token 已过期，请重新登录' })
  }
}
