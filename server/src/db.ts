import Database from 'better-sqlite3'
import path from 'node:path'
import fs from 'node:fs'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const DATA_DIR = path.join(__dirname, '..', 'data')

if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true })
}

const DB_PATH = process.env.DB_PATH || path.join(DATA_DIR, 'quiz-app.db')

let db: Database.Database

export function getDb(): Database.Database {
  if (!db) {
    db = new Database(DB_PATH)
    db.pragma('journal_mode = WAL')
    db.pragma('foreign_keys = ON')
    initSchema(db)
  }
  return db
}

function initSchema(db: Database.Database) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS users (
      id TEXT PRIMARY KEY,
      username TEXT UNIQUE NOT NULL,
      email TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL,
      created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS questions (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL REFERENCES users(id),
      chapter TEXT NOT NULL,
      question_number TEXT NOT NULL,
      original_number TEXT NOT NULL,
      problem TEXT NOT NULL,
      image TEXT,
      wrong_answer TEXT DEFAULT '',
      wrong_reason TEXT DEFAULT '',
      correct_answer TEXT DEFAULT '',
      steps TEXT DEFAULT '',
      summary TEXT DEFAULT '',
      knowledge_points TEXT DEFAULT '[]',
      workbook_id TEXT DEFAULT 'default',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS cards (
      question_id TEXT NOT NULL,
      user_id TEXT NOT NULL REFERENCES users(id),
      ease REAL DEFAULT 2.5,
      "interval" INTEGER DEFAULT 0,
      repetitions INTEGER DEFAULT 0,
      next_review TEXT NOT NULL,
      last_review TEXT,
      total_attempts INTEGER DEFAULT 0,
      total_correct INTEGER DEFAULT 0,
      favorited INTEGER DEFAULT 0,
      PRIMARY KEY (question_id, user_id)
    );

    CREATE TABLE IF NOT EXISTS wrong_records (
      id TEXT PRIMARY KEY,
      question_id TEXT NOT NULL,
      user_id TEXT NOT NULL REFERENCES users(id),
      date TEXT NOT NULL,
      wrong_answer TEXT DEFAULT '',
      wrong_reason TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS review_logs (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL REFERENCES users(id),
      question_id TEXT NOT NULL,
      rating TEXT NOT NULL,
      date TEXT NOT NULL,
      mode TEXT,
      choice_selected TEXT,
      choice_correct INTEGER,
      time_spent INTEGER
    );

    CREATE TABLE IF NOT EXISTS workbooks (
      id TEXT NOT NULL,
      user_id TEXT NOT NULL REFERENCES users(id),
      name TEXT NOT NULL,
      description TEXT DEFAULT '',
      created_at TEXT NOT NULL,
      PRIMARY KEY (id, user_id)
    );

    CREATE TABLE IF NOT EXISTS api_keys (
      user_id TEXT PRIMARY KEY REFERENCES users(id),
      deepseek_key_encrypted TEXT,
      qwen_key_encrypted TEXT
    );

    CREATE TABLE IF NOT EXISTS refresh_tokens (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL REFERENCES users(id),
      token_hash TEXT NOT NULL,
      expires_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_questions_user ON questions(user_id);
    CREATE INDEX IF NOT EXISTS idx_cards_user_next ON cards(user_id, next_review);
    CREATE INDEX IF NOT EXISTS idx_logs_user_date ON review_logs(user_id, date);
    CREATE INDEX IF NOT EXISTS idx_workbooks_user ON workbooks(user_id);
    CREATE INDEX IF NOT EXISTS idx_wrong_records_qid ON wrong_records(question_id);
  `)
}

export function closeDb() {
  if (db) {
    db.close()
  }
}
