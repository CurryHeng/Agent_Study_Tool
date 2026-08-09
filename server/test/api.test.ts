// ═══════════════════════════════════════════════════════════════════════════════
//  IMPORTANT: set DB_PATH to :memory: BEFORE any server modules are imported
// ═══════════════════════════════════════════════════════════════════════════════
process.env.DB_PATH = ':memory:'
process.env.JWT_SECRET = 'test-secret-for-api-tests'

import { describe, it, expect, beforeAll, afterAll } from 'vitest'
import request from 'supertest'
import express from 'express'

// Now safe: DB_PATH is :memory:, a brand-new sqlite db will be created on
// the first getDb() call and all routes / middleware share the same instance.
import { getDb, closeDb } from '../src/db.js'
import authRoutes from '../src/routes/auth.js'

// ── Build the Express app under test ───────────────────────────────────────────
const app = express()

app.use(express.json({ limit: '2mb' }))
app.use('/api/auth', authRoutes)

app.get('/api/health', (_req, res) => {
  res.json({ ok: true, timestamp: new Date().toISOString() })
})

// ── Shared test state ─────────────────────────────────────────────────────────
let accessToken: string
let refreshToken: string
const testUser = {
  username: 'testuser_' + Date.now(),
  email: 'test_' + Date.now() + '@example.com',
  password: 'password123',
}

// ── Tests ─────────────────────────────────────────────────────────────────────
describe('API endpoint tests', () => {
  beforeAll(() => {
    // Trigger DB init so tables exist before tests run
    getDb()
  })

  afterAll(() => {
    closeDb()
  })

  // ── Health ───────────────────────────────────────────────────────────────────
  describe('GET /api/health', () => {
    it('should return {ok: true}', async () => {
      const res = await request(app).get('/api/health')
      expect(res.status).toBe(200)
      expect(res.body.ok).toBe(true)
    })
  })

  // ── Register ─────────────────────────────────────────────────────────────────
  describe('POST /api/auth/register', () => {
    it('should return 201 with tokens for valid registration', async () => {
      const res = await request(app)
        .post('/api/auth/register')
        .send(testUser)

      expect(res.status).toBe(201)
      expect(res.body.user).toBeDefined()
      expect(res.body.user.username).toBe(testUser.username)
      expect(res.body.user.email).toBe(testUser.email)
      expect(res.body.accessToken).toBeTruthy()
      expect(res.body.refreshToken).toBeTruthy()

      // Save tokens for subsequent tests
      accessToken = res.body.accessToken
      refreshToken = res.body.refreshToken
    })

    it('should return 409 for duplicate email', async () => {
      const res = await request(app)
        .post('/api/auth/register')
        .send(testUser)

      expect(res.status).toBe(409)
      expect(res.body.error).toBeDefined()
    })

    it('should return 400 for missing fields', async () => {
      const res = await request(app)
        .post('/api/auth/register')
        .send({ username: 'x' })

      expect(res.status).toBe(400)
    })

    it('should return 400 for short password', async () => {
      const res = await request(app)
        .post('/api/auth/register')
        .send({ username: 'u2', email: 'e2@x.com', password: '1234567' })

      expect(res.status).toBe(400)
    })
  })

  // ── Login ────────────────────────────────────────────────────────────────────
  describe('POST /api/auth/login', () => {
    it('should return 200 with tokens for valid credentials', async () => {
      const res = await request(app)
        .post('/api/auth/login')
        .send({ email: testUser.email, password: testUser.password })

      expect(res.status).toBe(200)
      expect(res.body.accessToken).toBeTruthy()
      expect(res.body.refreshToken).toBeTruthy()
      expect(res.body.user.username).toBe(testUser.username)

      // Update tokens
      accessToken = res.body.accessToken
      refreshToken = res.body.refreshToken
    })

    it('should return 401 for wrong password', async () => {
      const res = await request(app)
        .post('/api/auth/login')
        .send({ email: testUser.email, password: 'wrongpass' })

      expect(res.status).toBe(401)
    })

    it('should return 401 for non-existent email', async () => {
      const res = await request(app)
        .post('/api/auth/login')
        .send({ email: 'noone@nowhere.com', password: 'anything123' })

      expect(res.status).toBe(401)
    })

    it('should return 400 for missing credentials', async () => {
      const res = await request(app)
        .post('/api/auth/login')
        .send({})

      expect(res.status).toBe(400)
    })
  })

  // ── Auth Me ──────────────────────────────────────────────────────────────────
  describe('GET /api/auth/me', () => {
    it('should return 401 without token', async () => {
      const res = await request(app).get('/api/auth/me')
      expect(res.status).toBe(401)
    })

    it('should return 401 with malformed token', async () => {
      const res = await request(app)
        .get('/api/auth/me')
        .set('Authorization', 'Bearer garbage-token')
      expect(res.status).toBe(401)
    })

    it('should return user data with valid token', async () => {
      const res = await request(app)
        .get('/api/auth/me')
        .set('Authorization', `Bearer ${accessToken}`)

      expect(res.status).toBe(200)
      expect(res.body.user).toBeDefined()
      expect(res.body.user.username).toBe(testUser.username)
      expect(res.body.user.email).toBe(testUser.email)
    })
  })
})
