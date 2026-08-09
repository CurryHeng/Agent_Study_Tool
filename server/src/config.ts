const PORT = parseInt(process.env.PORT || '3002', 10)

export const config = {
  port: PORT,
  jwtSecret: process.env.JWT_SECRET || 'change-me-in-production-use-env-var',
  encryptionKey: process.env.ENCRYPTION_KEY,
  corsOrigin: process.env.CORS_ORIGIN || 'http://localhost:5173',
  nodeEnv: process.env.NODE_ENV || 'development',
}
