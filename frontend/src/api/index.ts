import { api, getRefreshToken, setAuth, uploadWithProgress } from './client'
import type {
  AnswerResult,
  Document,
  DocumentDetail,
  DueItem,
  Knowledge,
  MindMapNode,
  Question,
  ReviewCard,
  SimilarQuestion,
  Stats,
  User,
  Workbook,
  WrongRecord,
} from '../types'

// ── 认证 ────────────────────────────────────────────────
export const authApi = {
  async register(username: string, email: string, password: string) {
    const data = await api.post<{ user: User; access_token: string; refresh_token: string }>(
      '/auth/register',
      { username, email, password },
    )
    setAuth(data.access_token, data.refresh_token, data.user)
    return data
  },
  async login(email: string, password: string) {
    const data = await api.post<{ user: User; access_token: string; refresh_token: string }>(
      '/auth/login',
      { email, password },
    )
    setAuth(data.access_token, data.refresh_token, data.user)
    return data
  },
  me: () => api.get<User>('/auth/me'),
  logout: () => api.post('/auth/logout', { refresh_token: getRefreshToken() }),
}

// ── 练习册 ──────────────────────────────────────────────
export const workbookApi = {
  list: () => api.get<Workbook[]>('/workbooks'),
  create: (name: string, description?: string) =>
    api.post<Workbook>('/workbooks', { name, description }),
}

// ── 题库 ────────────────────────────────────────────────
export const questionApi = {
  list: (workbookId?: number) =>
    api.get<Question[]>(`/questions${workbookId != null ? `?workbook_id=${workbookId}` : ''}`),
  get: (id: number) => api.get<Question>(`/questions/${id}`),
  create: (body: Record<string, unknown>) => api.post<Question>('/questions', body),
  update: (id: number, body: Record<string, unknown>) => api.put<Question>(`/questions/${id}`, body),
  remove: (id: number) => api.del(`/questions/${id}`),
  similar: (id: number) => api.post<SimilarQuestion>(`/questions/${id}/similar`),
}

// ── 知识点 ──────────────────────────────────────────────
export const knowledgeApi = {
  list: (workbookId: number) => api.get<Knowledge[]>(`/knowledge?workbook_id=${workbookId}`),
}

// ── 刷题 ────────────────────────────────────────────────
export const reviewApi = {
  due: (limit = 20, favorites = false) =>
    api.get<DueItem[]>(`/review/due?limit=${limit}${favorites ? '&favorites=true' : ''}`),
  answer: (questionId: number, body: Record<string, unknown>) =>
    api.post<AnswerResult>(`/questions/${questionId}/answer`, body),
  favorite: (questionId: number) => api.post<ReviewCard>(`/review/${questionId}/favorite`),
}

// ── 错题本 ──────────────────────────────────────────────
export const wrongRecordApi = {
  list: () => api.get<WrongRecord[]>('/wrong-records'),
  update: (id: number, body: Record<string, unknown>) => api.put<WrongRecord>(`/wrong-records/${id}`, body),
}

// ── 思维导图 ────────────────────────────────────────────
export const mindmapApi = {
  get: (workbookId: number) =>
    api.get<{ root: MindMapNode }>(`/workbooks/${workbookId}/mindmap`),
}

// ── 文档 / 资料导入 ─────────────────────────────────────
export const documentApi = {
  list: (workbookId: number) => api.get<Document[]>(`/documents?workbook_id=${workbookId}`),
  get: (id: number) => api.get<DocumentDetail>(`/documents/${id}`),
  remove: (id: number) => api.del<{ ok: boolean }>(`/documents/${id}`),
  index: (id: number) => api.post<{ chunks: number }>(`/documents/${id}/index`),
  upload: (file: File, workbookId: number, onProgress?: (pct: number) => void) => {
    const form = new FormData()
    form.append('workbook_id', String(workbookId))
    form.append('file', file)
    return uploadWithProgress<DocumentDetail>('/documents/upload', form, onProgress || (() => {}))
  },
}

// ── 学习统计 ────────────────────────────────────────────
export const statsApi = {
  get: () => api.get<Stats>('/stats'),
}

// ── AI 助手 ─────────────────────────────────────────────
export const agentApi = {
  chat: (message: string, workbookId?: number) =>
    api.post<{ task_id: string; intent: string; result: Record<string, unknown> }>(
      '/agent/chat',
      { message, workbook_id: workbookId },
    ),
}
