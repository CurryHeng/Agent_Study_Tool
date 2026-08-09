import jwt from 'jsonwebtoken'
import crypto from 'node:crypto'

const DEFAULT_SECRET = 'change-me-in-production-use-env-var'
const SECRET = process.env.JWT_SECRET || DEFAULT_SECRET

if (process.env.NODE_ENV === 'production' && SECRET === DEFAULT_SECRET) {
  console.error('[FATAL] JWT_SECRET is still the default value. Set JWT_SECRET in your .env file before running in production.')
  process.exit(1)
}

const ACCESS_EXPIRES = '15m'
const REFRESH_BYTES = 64
const REFRESH_EXPIRES_MS = 30 * 24 * 60 * 60 * 1000 // 30 days

export interface TokenPayload {
  userId: string
  username: string
}

export function signAccessToken(payload: TokenPayload): string {
  return jwt.sign(payload, SECRET, { expiresIn: ACCESS_EXPIRES })
}

export function verifyAccessToken(token: string): TokenPayload {
  return jwt.verify(token, SECRET) as TokenPayload
}

export function generateRefreshToken(): string {
  return crypto.randomBytes(REFRESH_BYTES).toString('hex')
}

export function refreshTokenExpiry(): string {
  return new Date(Date.now() + REFRESH_EXPIRES_MS).toISOString()
}
