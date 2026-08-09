import { sqliteTable, text, integer, real, primaryKey } from 'drizzle-orm/sqlite-core'

// ── users ────────────────────────────────────────────────────────────────────
export const users = sqliteTable('users', {
  id: text('id').primaryKey(),
  username: text('username').notNull().unique(),
  email: text('email').notNull().unique(),
  password_hash: text('password_hash').notNull(),
  created_at: text('created_at').notNull(),
})

// ── questions ────────────────────────────────────────────────────────────────
export const questions = sqliteTable('questions', {
  id: text('id').primaryKey(),
  user_id: text('user_id').notNull().references(() => users.id),
  chapter: text('chapter').notNull(),
  question_number: text('question_number').notNull(),
  original_number: text('original_number').notNull(),
  problem: text('problem').notNull(),
  image: text('image'),
  wrong_answer: text('wrong_answer').default(''),
  wrong_reason: text('wrong_reason').default(''),
  correct_answer: text('correct_answer').default(''),
  steps: text('steps').default(''),
  summary: text('summary').default(''),
  knowledge_points: text('knowledge_points').default('[]'),
  workbook_id: text('workbook_id').default('default'),
  created_at: text('created_at').notNull(),
  updated_at: text('updated_at').notNull(),
})

// ── cards ────────────────────────────────────────────────────────────────────
export const cards = sqliteTable('cards', {
  question_id: text('question_id').notNull(),
  user_id: text('user_id').notNull().references(() => users.id),
  ease: real('ease').default(2.5),
  interval: integer('interval').default(0),
  repetitions: integer('repetitions').default(0),
  next_review: text('next_review').notNull(),
  last_review: text('last_review'),
  total_attempts: integer('total_attempts').default(0),
  total_correct: integer('total_correct').default(0),
  favorited: integer('favorited').default(0),
}, (table) => ({
  pk: primaryKey({ columns: [table.question_id, table.user_id] }),
}))

// ── wrong_records ────────────────────────────────────────────────────────────
export const wrongRecords = sqliteTable('wrong_records', {
  id: text('id').primaryKey(),
  question_id: text('question_id').notNull(),
  user_id: text('user_id').notNull().references(() => users.id),
  date: text('date').notNull(),
  wrong_answer: text('wrong_answer').default(''),
  wrong_reason: text('wrong_reason').default(''),
})

// ── review_logs ──────────────────────────────────────────────────────────────
export const reviewLogs = sqliteTable('review_logs', {
  id: text('id').primaryKey(),
  user_id: text('user_id').notNull().references(() => users.id),
  question_id: text('question_id').notNull(),
  rating: text('rating').notNull(),
  date: text('date').notNull(),
  mode: text('mode'),
  choice_selected: text('choice_selected'),
  choice_correct: integer('choice_correct'),
  time_spent: integer('time_spent'),
})

// ── workbooks ────────────────────────────────────────────────────────────────
export const workbooks = sqliteTable('workbooks', {
  id: text('id').notNull(),
  user_id: text('user_id').notNull().references(() => users.id),
  name: text('name').notNull(),
  description: text('description').default(''),
  created_at: text('created_at').notNull(),
}, (table) => ({
  pk: primaryKey({ columns: [table.id, table.user_id] }),
}))

// ── api_keys ─────────────────────────────────────────────────────────────────
export const apiKeys = sqliteTable('api_keys', {
  user_id: text('user_id').primaryKey().references(() => users.id),
  deepseek_key_encrypted: text('deepseek_key_encrypted'),
  qwen_key_encrypted: text('qwen_key_encrypted'),
})

// ── refresh_tokens ───────────────────────────────────────────────────────────
export const refreshTokens = sqliteTable('refresh_tokens', {
  id: text('id').primaryKey(),
  user_id: text('user_id').notNull().references(() => users.id),
  token_hash: text('token_hash').notNull(),
  expires_at: text('expires_at').notNull(),
})
