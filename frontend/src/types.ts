export interface User {
  id: number
  username: string
  email: string
  created_at?: string
}

export interface Workbook {
  id: number
  user_id: number
  name: string
  description: string | null
  created_at: string
  updated_at: string
}

export interface QuestionOption {
  id: number
  question_id: number
  option_key: string
  content: string
  sort_order: number
}

export type QuestionType =
  | 'single_choice'
  | 'multiple_choice'
  | 'true_false'
  | 'fill_blank'
  | 'short_answer'

export interface Question {
  id: number
  workbook_id: number
  knowledge_id: number | null
  type: QuestionType
  content: string
  answer: string
  analysis: string | null
  summary: string | null
  image: string | null
  difficulty: number
  source: string
  status: string
  original_number: string | null
  question_number: string | null
  knowledge_name: string | null
  created_at: string
  updated_at: string
  options: QuestionOption[]
}

export interface ReviewCard {
  question_id: number
  // FSRS-6 调度状态
  state: string
  step: number | null
  stability: number | null
  difficulty: number | null
  due: string
  last_review: string | null
  // 业务统计
  total_attempts: number
  total_correct: number
  favorited: number
}

export interface DueItem {
  question: Question
  card: ReviewCard
}

export interface WrongRecord {
  id: number
  question_id: number
  wrong_answer: string | null
  wrong_reason: string | null
  created_at: string
  question_content: string
  correct_answer: string
  question_type: string
  knowledge_name: string | null
}

export interface Knowledge {
  id: number
  workbook_id: number
  parent_id: number | null
  name: string
  description: string | null
  level: number
}

export interface MindMapNode {
  id: number
  label: string
  children: MindMapNode[]
}

export interface AnswerResult {
  is_correct: boolean | null
  correct_answer: string
  analysis: string | null
  rating: string
  card: ReviewCard
}

export interface SimilarQuestion {
  type: QuestionType
  content: string
  answer: string
  analysis: string | null
  difficulty: number
  options: { option_key: string; content: string; sort_order: number }[]
}

export interface GeneratedQuestion {
  type: QuestionType
  content: string
  answer: string
  analysis: string | null
  difficulty: number
  options: { option_key: string; content: string; sort_order: number }[]
}

export interface ReviewResult {
  passed: boolean
  score: number
  issues: string[]
}

export interface RejectedQuestion {
  question: GeneratedQuestion
  review: ReviewResult
}

export interface GenerateResult {
  saved: Question[]
  rejected: RejectedQuestion[]
}

export interface Document {
  id: number
  workbook_id: number
  filename: string
  file_type: string
  file_path: string
  file_size: number
  status: string
  created_at: string
}

export interface Section {
  title: string
  level: number
  paragraphs: string[]
}

export interface DocumentDetail extends Document {
  sections: Section[]
  generated_questions?: GeneratedQuestion[] | null
}

export interface Bucket {
  label: string
  count: number
}

export interface HeatmapItem {
  knowledge_id: number | null
  name: string
  total: number
  errors: number
}

export interface ActivityDay {
  date: string
  total: number
  correct: number
}

export interface ReasonItem {
  name: string
  count: number
}

export interface RecentRecord {
  date: string
  rating: string | null
  mode: string | null
  is_correct: number | null
  question_id: number
  question_content: string
}

export interface Stats {
  cards_total: number
  cards_due: number
  reviewed_today: number
  favorites: number
  question_total: number
  mastery: Record<string, number>
  accuracy_buckets: Bucket[]
  knowledge_heatmap: HeatmapItem[]
  activity_heatmap: ActivityDay[]
  wrong_reasons: ReasonItem[]
  recent: RecentRecord[]
  week_minutes: number
  week_days: number
}

// ── AI 助手（#45 按 Agent 接口契约 v2） ──────────────────
export interface AgentStep {
  id?: number
  tool: string
  status?: 'success' | 'failed'
  args?: Record<string, unknown> | null
  summary?: string | null
  error?: string | null
  /** 兼容旧字段 */
  ok?: boolean
}

export interface AgentProposal {
  proposal_id: string
  action: string
  target?: Record<string, unknown> | null
  changes?: Record<string, unknown> | null
  impact?: string | null
  expires_in_sec?: number | null
}

export interface AgentChatEntity {
  type?: 'knowledge_node' | 'question' | 'document' | 'workbook' | 'plan' | null
  id?: number | null
}

export interface AgentChatContext {
  route?: string | null
  entity?: AgentChatEntity | null
}

export type AgentChatStatus = 'completed' | 'waiting_confirm' | 'failed' | 'need_input'

export interface AgentChatResponse {
  task_id?: string | null
  status?: AgentChatStatus | null
  conversation_id?: number | null
  reply: string
  steps?: AgentStep[] | null
  proposals?: AgentProposal[] | null
  navigate?: string | null
  error?: { code?: string; message?: string } | null
  /** 旧字段，deprecated */
  intent?: string | null
  result?: Record<string, unknown> | null
}

export interface AgentConfirmResponse {
  ok: boolean
  result?: Record<string, unknown> | null
}

// ── 会话列表（#47） ─────────────────────────────────────
export interface Conversation {
  id: number
  title: string | null
  created_at: string
  updated_at: string
  last_message?: string | null
}

export interface ConversationMessage {
  id: number
  conversation_id: number
  role: 'user' | 'assistant'
  content: string
  metadata?: Record<string, unknown> | null
  created_at: string
}

// ── 学习活动时间线（#59） ──────────────────────────────
export interface HistoryEvent {
  id: string
  type: 'upload' | 'generate' | 'answer' | 'wrong' | 'review'
  title: string
  detail?: string | null
  created_at: string
}

// ── 知识图谱（#58） ─────────────────────────────────────
export interface KnowledgeGraphNode {
  id: number
  name: string
  parent_id: number | null
  level: number
}

export interface KnowledgeGraphEdge {
  source: number
  target: number
  type: string
  label?: string | null
}

export interface KnowledgeGraph {
  nodes: KnowledgeGraphNode[]
  edges: KnowledgeGraphEdge[]
}

// ── AI 供应商设置（设置页） ─────────────────────────────
export interface AiProviderConfig {
  provider: string
  api_key?: string
  model?: string
}

export interface AiSettings {
  text: AiProviderConfig
  multimodal: AiProviderConfig
}
