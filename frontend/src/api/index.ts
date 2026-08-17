import { api, getRefreshToken, setAuth, uploadWithProgress } from './client'
import type {
  AgentChatContext,
  AgentChatResponse,
  AgentConfirmResponse,
  AiSettings,
  Conversation,
  ConversationMessage,
  HistoryEvent,
  KnowledgeGraph,
  AnswerResult,
  Document,
  DocumentDetail,
  DueItem,
  GenerateResult,
  GradeResult,
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
  remove: (id: number) => api.del<{ ok: boolean }>(`/workbooks/${id}`),
}

// ── 题库 ────────────────────────────────────────────────
export const questionApi = {
  list: (options: { workbookId?: number | null; page?: number; pageSize?: number } = {}) => {
    const params = new URLSearchParams()
    if (options.workbookId != null) params.set('workbook_id', String(options.workbookId))
    if (options.page != null) params.set('page', String(options.page))
    if (options.pageSize != null) params.set('page_size', String(options.pageSize))
    const qs = params.toString()
    return api.get<Question[]>(`/questions${qs ? `?${qs}` : ''}`)
  },
  get: (id: number) => api.get<Question>(`/questions/${id}`),
  create: (body: Record<string, unknown>) => api.post<Question>('/questions', body),
  update: (id: number, body: Record<string, unknown>) => api.put<Question>(`/questions/${id}`, body),
  remove: (id: number) => api.del(`/questions/${id}`),
  similar: (id: number) => api.post<SimilarQuestion>(`/questions/${id}/similar`),
  generate: (body: {
    workbook_id: number
    knowledge_id?: number | null
    type: string
    count: number
    difficulty: number
  }) => api.post<GenerateResult>('/questions/generate', body),
}

// ── 知识点 ──────────────────────────────────────────────
export interface KnowledgeSuggestion {
  name: string
  description: string | null
}

export const knowledgeApi = {
  list: (workbookId: number, page?: number, pageSize?: number) => {
    const params = new URLSearchParams({ workbook_id: String(workbookId) })
    if (page != null) params.set('page', String(page))
    if (pageSize != null) params.set('page_size', String(pageSize))
    return api.get<Knowledge[]>(`/knowledge?${params.toString()}`)
  },
  create: (body: Record<string, unknown>) => api.post<Knowledge>('/knowledge', body),
  suggestChildren: (knowledgeId: number) =>
    api.post<{ suggestions: KnowledgeSuggestion[] }>(`/knowledge/${knowledgeId}/suggest-children`),
}

// ── 刷题 ────────────────────────────────────────────────
export const reviewApi = {
  due: (limit = 20, favorites = false, includeAll = false) =>
    api.get<DueItem[]>(
      `/review/due?limit=${limit}${favorites ? '&favorites=true' : ''}${includeAll ? '&include_all=true' : ''}`,
    ),
  answer: (questionId: number, body: Record<string, unknown>) =>
    api.post<AnswerResult>(`/questions/${questionId}/answer`, body),
  grade: (questionId: number, userAnswer: string | null) =>
    api.post<GradeResult>(`/questions/${questionId}/grade`, { user_answer: userAnswer }),
  favorite: (questionId: number) => api.post<ReviewCard>(`/review/${questionId}/favorite`),
}

// ── 错题本 ──────────────────────────────────────────────
export const wrongRecordApi = {
  list: (options: {
    knowledgeId?: number | null
    questionType?: string | null
    page?: number
    pageSize?: number
  } = {}) => {
    const params = new URLSearchParams()
    if (options.knowledgeId != null) params.set('knowledge_id', String(options.knowledgeId))
    if (options.questionType) params.set('question_type', options.questionType)
    if (options.page != null) params.set('page', String(options.page))
    if (options.pageSize != null) params.set('page_size', String(options.pageSize))
    const qs = params.toString()
    return api.get<WrongRecord[]>(`/wrong-records${qs ? `?${qs}` : ''}`)
  },
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
  upload: (
    file: File,
    workbookId: number,
    options?: {
      autoGenerate?: boolean
      questionType?: string
      count?: number
      difficulty?: number
      scope?: string
    },
    onProgress?: (pct: number) => void,
  ) => {
    const form = new FormData()
    form.append('workbook_id', String(workbookId))
    form.append('file', file)
    if (options?.autoGenerate) form.append('auto_generate', 'true')
    if (options?.questionType) form.append('question_type', options.questionType)
    if (options?.count != null) form.append('count', String(options.count))
    if (options?.difficulty != null) form.append('difficulty', String(options.difficulty))
    if (options?.scope) form.append('scope', options.scope)
    return uploadWithProgress<DocumentDetail>('/documents/upload', form, onProgress || (() => {}))
  },
}

// ── 学习统计 ────────────────────────────────────────────
export const statsApi = {
  get: () => api.get<Stats>('/stats'),
}

// ── 学习活动时间线（#59） ─────────────────────────────────
export const historyApi = {
  list: (limit = 100) => api.get<HistoryEvent[]>(`/history?limit=${limit}`),
}

// ── 知识图谱（#58） ──────────────────────────────────────
export const knowledgeGraphApi = {
  get: (workbookId: number) =>
    api.get<KnowledgeGraph>(`/knowledge-graph?workbook_id=${workbookId}`),
}

// ── AI 供应商设置 ────────────────────────────────────────
export const settingsApi = {
  getAi: () => api.get<AiSettings>('/settings/ai'),
  updateAi: (payload: AiSettings) => api.put<AiSettings>('/settings/ai', payload),
}

// ── 会话（#47） ──────────────────────────────────────────
export const conversationApi = {
  list: () => api.get<Conversation[]>('/conversations'),
  create: (title?: string) => api.post<Conversation>('/conversations', { title }),
  messages: (id: number, limit = 50, offset = 0) =>
    api.get<ConversationMessage[]>(`/conversations/${id}/messages?limit=${limit}&offset=${offset}`),
  remove: (id: number) => api.del<{ ok: boolean }>(`/conversations/${id}`),
}

// ── AI 助手 ─────────────────────────────────────────────
// #33 新契约：POST /api/agent/chat 返回 reply + steps[] + proposals[] + navigate
export const agentApi = {
  chat: (
    message: string,
    options: {
      workbookId?: number | null
      conversationId?: number | null
      context?: AgentChatContext | null
    } = {},
  ) => {
    const body: Record<string, unknown> = { message }
    if (options.workbookId != null) body.workbook_id = options.workbookId
    if (options.conversationId != null) body.conversation_id = options.conversationId
    if (options.context) body.context = options.context
    return api.post<AgentChatResponse>('/agent/chat', body)
  },
  confirm: (proposalId: string, approved: boolean) =>
    api.post<AgentConfirmResponse>('/agent/confirm', { proposal_id: proposalId, approved }),
}
