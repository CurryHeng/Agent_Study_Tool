import type { ReviewCard, ReviewLog, Question, Workbook } from '../types'
import { cardsApi, questionsApi, logsApi, workbooksApi, syncApi, isAuthenticated } from '../api/client'

const CARDS_KEY = 'quiz-app-cards'
const LOGS_KEY = 'quiz-app-logs'
const USER_QUESTIONS_KEY = 'quiz-app-user-questions'
const WORKBOOKS_KEY = 'quiz-app-workbooks'
const PENDING_SYNC_KEY = 'quiz-app-pending-sync'

export const DEFAULT_WORKBOOK_ID = 'default'

const DEFAULT_WORKBOOK: Workbook = {
  id: DEFAULT_WORKBOOK_ID,
  name: '默认练习册',
  description: '默认练习册',
  createdAt: '2024-01-01',
}

// ── Pending sync tracking ──

function markPendingSync() {
  localStorage.setItem(PENDING_SYNC_KEY, 'true')
}

export function hasPendingSync(): boolean {
  return localStorage.getItem(PENDING_SYNC_KEY) === 'true'
}

function clearPendingSync() {
  localStorage.removeItem(PENDING_SYNC_KEY)
}

// ── API-aware write helpers ──

async function tryApi<T>(fn: () => Promise<T>): Promise<boolean> {
  if (!isAuthenticated()) return false
  try {
    await fn()
    return true
  } catch {
    markPendingSync()
    return false
  }
}

export function loadCards(): ReviewCard[] {
  try {
    const raw = localStorage.getItem(CARDS_KEY)
    if (!raw) return []
    const cards: ReviewCard[] = JSON.parse(raw)
    // Backward compat: add new fields with defaults
    for (const c of cards) {
      if (c.totalAttempts === undefined) c.totalAttempts = 0
      if (c.totalCorrect === undefined) c.totalCorrect = 0
      if (c.favorited === undefined) c.favorited = false
      if (c.wrongRecords === undefined) c.wrongRecords = []
    }
    return cards
  } catch {
    return []
  }
}

export function saveCards(cards: ReviewCard[]) {
  localStorage.setItem(CARDS_KEY, JSON.stringify(cards))
}

export function toggleFavorite(cards: ReviewCard[], questionId: string): ReviewCard[] {
  return cards.map((c) => (c.questionId === questionId ? { ...c, favorited: !c.favorited } : c))
}

export function loadLogs(): ReviewLog[] {
  try {
    const raw = localStorage.getItem(LOGS_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

export function saveLogs(logs: ReviewLog[]) {
  localStorage.setItem(LOGS_KEY, JSON.stringify(logs))
}

export function loadUserQuestions(): Question[] {
  try {
    const raw = localStorage.getItem(USER_QUESTIONS_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

export function saveUserQuestions(questions: Question[]) {
  localStorage.setItem(USER_QUESTIONS_KEY, JSON.stringify(questions))
}

export function addUserQuestion(question: Question) {
  const existing = loadUserQuestions()
  if (existing.some((q) => q.id === question.id)) return
  existing.push(question)
  saveUserQuestions(existing)
}

// ── Chapter ordering ──

const CN_NUM: Record<string, number> = {
  '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
  '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
}
const CN_NUM_REV: Record<string, number> = {
  '十一': 11, '十二': 12, '十三': 13, '十四': 14, '十五': 15,
  '十六': 16, '十七': 17, '十八': 18, '十九': 19, '二十': 20,
}

function parseChapterNumber(chapter: string): number {
  // Match 第X章 or 第XX章
  const m = chapter.match(/^第(.+?)章/)
  if (!m) return 999 // unknown, push to end
  const cn = m[1]
  if (CN_NUM_REV[cn] !== undefined) return CN_NUM_REV[cn]
  let num = 0
  if (cn.startsWith('十')) {
    // "十X" → 10+X (11-19)
    num = 10 + (CN_NUM[cn[1]] || 0)
  } else if (cn.endsWith('十')) {
    // "X十" → X*10 (20, 30, 40, ..., 90)
    num = (CN_NUM[cn[0]] || 0) * 10
  } else if (cn.length === 3 && CN_NUM[cn[0]] && CN_NUM[cn[2]]) {
    // "X十Y" → X*10 + Y (21-99, 如 "二十一", "九十九")
    num = CN_NUM[cn[0]] * 10 + CN_NUM[cn[2]]
  } else if (cn.length === 1) {
    num = CN_NUM[cn] || 999
  } else {
    num = 999
  }
  return num
}

/** Sort chapter names by Chinese numeric order: 第一章, 第二章, ..., 第十章 */
export function sortChapters(chapters: string[]): string[] {
  return [...chapters].sort((a, b) => parseChapterNumber(a) - parseChapterNumber(b))
}

/** Sort chapter-question entries by chapter numeric order */
export function sortChapterEntries<K>(entries: [string, K][]): [string, K][] {
  return [...entries].sort((a, b) => parseChapterNumber(a[0]) - parseChapterNumber(b[0]))
}

export function getStats(cards: ReviewCard[]) {
  const today = new Date().toISOString().split('T')[0]
  const due = cards.filter((c) => c.nextReview <= today).length
  const total = cards.length
  const reviewed = cards.filter((c) => c.lastReview === today).length

  return { due, total, reviewed }
}

// ── Workbook management ──

export function loadWorkbooks(): Workbook[] {
  try {
    const raw = localStorage.getItem(WORKBOOKS_KEY)
    if (!raw) return [DEFAULT_WORKBOOK]
    const workbooks: Workbook[] = JSON.parse(raw)
    if (!workbooks.some((w) => w.id === DEFAULT_WORKBOOK_ID)) {
      workbooks.unshift(DEFAULT_WORKBOOK)
    }
    return workbooks
  } catch {
    return [DEFAULT_WORKBOOK]
  }
}

export function saveWorkbooks(workbooks: Workbook[]) {
  localStorage.setItem(WORKBOOKS_KEY, JSON.stringify(workbooks))
}

export function addWorkbook(name: string, description?: string): Workbook {
  const workbooks = loadWorkbooks()
  const wb: Workbook = {
    id: 'wb-' + Date.now(),
    name,
    description,
    createdAt: new Date().toISOString().split('T')[0],
  }
  workbooks.push(wb)
  saveWorkbooks(workbooks)
  return wb
}

export function getWorkbookId(q: Question): string {
  return q.workbookId || DEFAULT_WORKBOOK_ID
}

export function migrateUserQuestions() {
  const questions = loadUserQuestions()
  let changed = false
  for (const q of questions) {
    if (!q.workbookId) {
      q.workbookId = DEFAULT_WORKBOOK_ID
      changed = true
    }
  }
  if (changed) saveUserQuestions(questions)
}

// ── Delete ──

export function deleteUserQuestion(questionId: string): boolean {
  const questions = loadUserQuestions()
  const idx = questions.findIndex((q) => q.id === questionId)
  if (idx === -1) return false
  questions.splice(idx, 1)
  saveUserQuestions(questions)
  return true
}

export function deleteCard(questionId: string): boolean {
  const cards = loadCards()
  const idx = cards.findIndex((c) => c.questionId === questionId)
  if (idx === -1) return false
  cards.splice(idx, 1)
  saveCards(cards)
  return true
}

export function isUserQuestion(id: string): boolean {
  return id.startsWith('user-')
}

// ── Auto-numbering ──

export function getNextQuestionNumber(chapter: string, allQuestions: Question[]): string {
  const chapterNum = parseChapterNumber(chapter)
  if (chapterNum === 999) return ''
  const chapterQuestions = allQuestions.filter((q) => q.chapter === chapter)
  let maxSeq = 0
  for (const q of chapterQuestions) {
    const parts = q.questionNumber.split('.')
    if (parts.length === 2 && parseInt(parts[0]) === chapterNum) {
      const seq = parseInt(parts[1])
      if (!isNaN(seq) && seq > maxSeq) maxSeq = seq
    }
  }
  return `${chapterNum}.${maxSeq + 1}`
}

// ── API-aware writes (try API first, localStorage as fallback) ──

export async function saveCardsRemote(cards: ReviewCard[]) {
  localStorage.setItem(CARDS_KEY, JSON.stringify(cards))
  for (const card of cards) {
    await tryApi(() => cardsApi.update(card.questionId, card))
  }
}

export async function saveLogsRemote(logs: ReviewLog[]) {
  localStorage.setItem(LOGS_KEY, JSON.stringify(logs))
  await tryApi(() => logsApi.create(logs))
}

export async function addUserQuestionRemote(question: Question) {
  addUserQuestion(question) // local save
  await tryApi(() => questionsApi.create(question))
}

export async function deleteUserQuestionRemote(id: string) {
  deleteUserQuestion(id)
  await tryApi(() => questionsApi.delete(id))
}

export async function addWorkbookRemote(name: string, description?: string): Promise<Workbook> {
  const wb = addWorkbook(name, description)
  await tryApi(() => workbooksApi.create(name, description))
  return wb
}

export async function toggleFavoriteRemote(cards: ReviewCard[], questionId: string): Promise<ReviewCard[]> {
  const updated = toggleFavorite(cards, questionId)
  const target = updated.find((c) => c.questionId === questionId)
  if (target) {
    await tryApi(() => cardsApi.toggleFavorite(questionId))
  }
  return updated
}

// ── Sync: upload local data to server then download full server state ──

export async function syncAll(): Promise<{
  success: boolean
  uploaded: number
  downloaded: any
}> {
  if (!isAuthenticated()) return { success: false, uploaded: 0, downloaded: null }

  try {
    const clientData = {
      questions: loadUserQuestions(),
      cards: loadCards(),
      logs: loadLogs(),
      workbooks: loadWorkbooks().filter((w) => w.id !== DEFAULT_WORKBOOK_ID),
    }

    const result = await syncApi.push(clientData)

    // Overwrite localStorage with server data
    if (result.data) {
      if (result.data.questions) saveUserQuestions(result.data.questions)
      if (result.data.cards) {
        // Map server card fields back to client format
        const mapped = result.data.cards.map((c: any) => ({
          questionId: c.question_id,
          ease: c.ease,
          interval: c.interval,
          repetitions: c.repetitions,
          nextReview: c.next_review,
          lastReview: c.last_review,
          totalAttempts: c.total_attempts,
          totalCorrect: c.total_correct,
          favorited: !!c.favorited,
          wrongRecords: [],
        }))
        saveCards(mapped)
      }
      if (result.data.logs) {
        const localLogs = loadLogs()
        const serverIds = new Set(result.data.logs.map((l: any) => l.id))
        const merged = [...result.data.logs, ...localLogs.filter((l: any) => !serverIds.has(l.id))]
        saveLogs(merged)
      }
      if (result.data.workbooks) {
        const mWb = result.data.workbooks.map((w: any) => ({
          id: w.id,
          name: w.name,
          description: w.description,
          createdAt: w.created_at,
        }))
        saveWorkbooks(mWb)
      }
    }

    clearPendingSync()
    return {
      success: true,
      uploaded: (result.changes?.questions || 0) + (result.changes?.cards || 0) + (result.changes?.logs || 0),
      downloaded: result.data,
    }
  } catch {
    markPendingSync()
    return { success: false, uploaded: 0, downloaded: null }
  }
}

// ── Pull all data from server (login/device switch) ──

export async function pullAllFromServer(): Promise<boolean> {
  if (!isAuthenticated()) return false
  try {
    const result = await syncApi.push({ clientData: {} })
    if (result.data) {
      if (result.data.questions) saveUserQuestions(result.data.questions)
      if (result.data.cards) {
        const mapped = result.data.cards.map((c: any) => ({
          questionId: c.question_id,
          ease: c.ease,
          interval: c.interval,
          repetitions: c.repetitions,
          nextReview: c.next_review,
          lastReview: c.last_review,
          totalAttempts: c.total_attempts,
          totalCorrect: c.total_correct,
          favorited: !!c.favorited,
          wrongRecords: [],
        }))
        saveCards(mapped)
      }
      if (result.data.logs) {
        const localLogs = loadLogs()
        const serverIds = new Set(result.data.logs.map((l: any) => l.id))
        const merged = [...result.data.logs, ...localLogs.filter((l: any) => !serverIds.has(l.id))]
        saveLogs(merged)
      }
      if (result.data.workbooks) {
        const mWb = result.data.workbooks.map((w: any) => ({
          id: w.id,
          name: w.name,
          description: w.description,
          createdAt: w.created_at,
        }))
        saveWorkbooks(mWb)
      }
    }
    clearPendingSync()
    return true
  } catch {
    return false
  }
}
