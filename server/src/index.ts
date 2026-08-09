import express from 'express'
import cors from 'cors'
import helmet from 'helmet'
import rateLimit from 'express-rate-limit'
import { config } from './config.js'
import { getDb, closeDb } from './db.js'
import authRoutes from './routes/auth.js'
import questionRoutes from './routes/questions.js'
import cardRoutes from './routes/cards.js'
import logRoutes from './routes/logs.js'
import workbookRoutes from './routes/workbooks.js'
import syncRoutes from './routes/sync.js'

const app = express()

// Security
app.use(helmet({
  crossOriginResourcePolicy: { policy: 'cross-origin' },
  contentSecurityPolicy: false,
}))
app.use(cors({
  origin: config.corsOrigin,
  credentials: true,
}))

// Rate limiting
const apiLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 120,
  standardHeaders: true,
  legacyHeaders: false,
})

const authLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 10,
  standardHeaders: true,
  legacyHeaders: false,
})

app.use('/api/auth', authLimiter)
app.use('/api', apiLimiter)

// Body parsing (2MB for images)
app.use(express.json({ limit: '2mb' }))

// Routes
app.use('/api/auth', authRoutes)
app.use('/api/questions', questionRoutes)
app.use('/api/cards', cardRoutes)
app.use('/api/logs', logRoutes)
app.use('/api/workbooks', workbookRoutes)
app.use('/api/sync', syncRoutes)

// Health check
app.get('/api/health', (_req, res) => {
  res.json({ ok: true, timestamp: new Date().toISOString() })
})

// Initialize DB on startup
getDb()
console.log('Database initialized')

// Start
const server = app.listen(config.port, () => {
  console.log(`Server running on http://localhost:${config.port}`)
})

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\nShutting down...')
  closeDb()
  server.close()
  process.exit(0)
})

process.on('SIGTERM', () => {
  closeDb()
  server.close()
  process.exit(0)
})
