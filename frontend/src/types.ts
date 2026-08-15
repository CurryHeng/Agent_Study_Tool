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

// ── AI 助手（#33 AgentChatView 新契约） ──────────────────
export interface AgentStep {
  tool: string
  args?: Record<string, unknown> | null
  ok: boolean
  summary?: string | null
}

export interface AgentProposal {
  proposal_id: string
  action: string
  target?: Record<string, unknown> | null
  changes?: Record<string, unknown> | null
  impact?: string | null
  expires_in_sec?: number | null
}

export interface AgentChatContext {
  view?: string | null
  selected_knowledge_id?: number | null
  current_question_id?: number | null
}

export interface AgentChatResponse {
  task_id?: string | null
  conversation_id?: number | null
  reply: string
  steps?: AgentStep[] | null
  proposals?: AgentProposal[] | null
  navigate?: string | null
}

export interface AgentConfirmResponse {
  ok: boolean
  result?: Record<string, unknown> | null
}
