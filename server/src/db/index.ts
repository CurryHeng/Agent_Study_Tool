import { drizzle } from 'drizzle-orm/better-sqlite3'
import type { BetterSQLite3Database } from 'drizzle-orm/better-sqlite3'
import { getDb as getSqliteDb } from '../db.js'
import * as schema from './schema.js'

let drizzleDb: BetterSQLite3Database<typeof schema> | null = null

export function getDrizzle(): BetterSQLite3Database<typeof schema> {
  if (!drizzleDb) {
    const sqlite = getSqliteDb()
    drizzleDb = drizzle(sqlite, { schema })
  }
  return drizzleDb
}
