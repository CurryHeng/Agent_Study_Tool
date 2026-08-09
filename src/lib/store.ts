import { create } from 'zustand'
import type { Question, ReviewCard, ReviewLog, Workbook, WrongRecord } from './schema'

// ====== Store 接口 ======
interface AppState {
  // 数据
  cards: ReviewCard[]
  logs: ReviewLog[]
  userQuestions: Question[]
  workbooks: Workbook[]
  builtInQuestions: Question[]

  // 认证
  accessToken: string | null
  refreshToken: string | null
  user: { id: string; username: string; email: string } | null

  // Actions — Cards
  setCards: (cards: ReviewCard[]) => void
  updateCard: (questionId: string, updates: Partial<ReviewCard>) => void
  addCard: (card: ReviewCard) => void
  removeCard: (questionId: string) => void
  toggleFavorite: (questionId: string) => void
  addWrongRecord: (questionId: string, record: WrongRecord) => void

  // Actions — Questions
  setUserQuestions: (qs: Question[]) => void
  addUserQuestion: (q: Question) => void
  removeUserQuestion: (id: string) => void
  setBuiltInQuestions: (qs: Question[]) => void

  // Actions — Logs
  setLogs: (logs: ReviewLog[]) => void
  addLog: (log: ReviewLog) => void

  // Actions — Workbooks
  setWorkbooks: (wbs: Workbook[]) => void
  addWorkbook: (wb: Workbook) => void

  // Actions — Auth
  setAuth: (access: string, refresh: string, user: { id: string; username: string; email: string }) => void
  clearAuth: () => void

  // 计算属性
  allQuestions: () => Question[]
  dueCards: () => ReviewCard[]
  stats: () => { due: number; total: number; reviewed: number }
}

// ====== Store 实现 ======
export const useAppStore = create<AppState>()((set, get) => ({
  // 初始值
  cards: [],
  logs: [],
  userQuestions: [],
  workbooks: [
    { id: 'agent-ch1', name: '第1章：AI Agent 概述', description: 'Agent 核心概念 · ReAct · Harness · 编排模式', createdAt: new Date().toISOString().split('T')[0] },
    { id: 'agent-ch2', name: '第2章：上下文工程', description: 'KV Cache · 注意力 · 提示工程 · Skills · 压缩', createdAt: new Date().toISOString().split('T')[0] },
  ],
  builtInQuestions: [],
  accessToken: null,
  refreshToken: null,
  user: null,

  // Cards
  setCards: (cards) => set({ cards }),
  updateCard: (questionId, updates) =>
    set((s) => ({
      cards: s.cards.map((c) => (c.questionId === questionId ? { ...c, ...updates } : c)),
    })),
  addCard: (card) =>
    set((s) => ({ cards: [...s.cards, card] })),
  removeCard: (questionId) =>
    set((s) => ({ cards: s.cards.filter((c) => c.questionId !== questionId) })),
  toggleFavorite: (questionId) =>
    set((s) => ({
      cards: s.cards.map((c) =>
        c.questionId === questionId ? { ...c, favorited: !c.favorited } : c
      ),
    })),
  addWrongRecord: (questionId, record) =>
    set((s) => ({
      cards: s.cards.map((c) =>
        c.questionId === questionId
          ? { ...c, wrongRecords: [...c.wrongRecords, record] }
          : c
      ),
    })),

  // Questions
  setUserQuestions: (qs) => set({ userQuestions: qs }),
  addUserQuestion: (q) =>
    set((s) => ({ userQuestions: [...s.userQuestions, q] })),
  removeUserQuestion: (id) =>
    set((s) => ({ userQuestions: s.userQuestions.filter((q) => q.id !== id) })),
  setBuiltInQuestions: (qs) => set({ builtInQuestions: qs }),

  // Logs
  setLogs: (logs) => set({ logs }),
  addLog: (log) => set((s) => ({ logs: [...s.logs, log] })),

  // Workbooks
  setWorkbooks: (wbs) => set({ workbooks: wbs }),
  addWorkbook: (wb) => set((s) => ({ workbooks: [...s.workbooks, wb] })),

  // Auth
  setAuth: (accessToken, refreshToken, user) =>
    set({ accessToken, refreshToken, user }),
  clearAuth: () =>
    set({ accessToken: null, refreshToken: null, user: null }),

  // 计算
  allQuestions: () => [...get().builtInQuestions, ...get().userQuestions],
  dueCards: () => {
    const today = new Date().toISOString().split('T')[0]
    return get().cards.filter((c) => c.nextReview <= today)
  },
  stats: () => {
    const { cards } = get()
    const today = new Date().toISOString().split('T')[0]
    return {
      due: cards.filter((c) => c.nextReview <= today).length,
      total: cards.length,
      reviewed: cards.filter((c) => c.lastReview === today).length,
    }
  },
}))
