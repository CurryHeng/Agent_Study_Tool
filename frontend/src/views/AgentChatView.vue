<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Bot,
  Check,
  ChevronDown,
  CircleCheck,
  CircleX,
  Loader2,
  MessageSquare,
  Navigation,
  Plus,
  Send,
  Sparkles,
  Trash2,
  X,
} from 'lucide-vue-next'
import { agentApi, conversationApi, workbookApi } from '../api'
import type {
  AgentChatContext,
  AgentProposal,
  AgentStep,
  Conversation,
  ConversationMessage,
  Workbook,
} from '../types'
import MarkdownContent from '../components/MarkdownContent.vue'

interface ProposalState {
  proposal: AgentProposal
  status: 'pending' | 'approved' | 'rejected'
}

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  steps?: AgentStep[]
  proposals?: ProposalState[]
  navigate?: string | null
  stepsOpen?: boolean
}

const route = useRoute()
const router = useRouter()

const workbooks = ref<Workbook[]>([])
const workbookId = ref<number | null>(null)
const conversations = ref<Conversation[]>([])
const activeConversationId = ref<number | null>(null)
const messages = ref<ChatMessage[]>([])
const input = ref('')
const loading = ref(false)
const error = ref('')
const listEl = ref<HTMLElement | null>(null)

const SUGGESTIONS = [
  '整理刚上传的资料',
  '帮我出 5 道选择题',
  '我哪里比较薄弱？',
  '今天该复习什么？',
]

// #41/#45 上下文注入：route + entity（当前页面与选中实体）
const context = computed<AgentChatContext>(() => ({
  route: String(route.path),
  entity: null, // 后续接入知识点/题目选中状态
}))

const ACTION_LABEL: Record<string, string> = {
  generate_questions: '生成题目',
  import_knowledge: '导入知识点',
  update_knowledge_node: '修改知识点',
  add_knowledge_node: '新增知识点',
  delete_knowledge_node: '删除知识点',
  update_question: '修改题目',
  delete_question: '删除题目',
  favorite_question: '收藏题目',
  analyze_wrong_reason: '分析错因',
  create_plan: '创建学习计划',
}

function actionLabel(action: string): string {
  return ACTION_LABEL[action] ?? action
}

function displayValue(value: unknown): string {
  if (value == null) return '—'
  if (typeof value === 'string') return value
  try {
    return JSON.stringify(value)
  } catch {
    return String(value)
  }
}

function targetSummary(proposal: AgentProposal): string {
  const t = proposal.target as Record<string, unknown> | null | undefined
  if (!t) return ''
  return displayValue(t.name ?? t.knowledge_id ?? t.question_id ?? '')
}

function changesSummary(proposal: AgentProposal): { before?: string; after?: string } {
  const c = proposal.changes as Record<string, unknown> | null | undefined
  if (!c) return {}
  return {
    before: c.before != null ? displayValue(c.before) : undefined,
    after: c.after != null ? displayValue(c.after) : undefined,
  }
}

function stepStatus(step: AgentStep): 'success' | 'failed' {
  if (step.status) return step.status
  return step.ok === false ? 'failed' : 'success'
}

async function scrollToBottom() {
  await nextTick()
  listEl.value?.scrollTo({ top: listEl.value.scrollHeight, behavior: 'smooth' })
}

async function loadConversations() {
  try {
    conversations.value = await conversationApi.list()
  } catch {
    // 会话接口尚未就绪时静默降级，聊天仍可用
  }
}

async function createConversation() {
  error.value = ''
  try {
    const conv = await conversationApi.create()
    conversations.value.unshift(conv)
    activeConversationId.value = conv.id
    messages.value = []
  } catch (e) {
    error.value = e instanceof Error ? e.message : '创建会话失败'
  }
}

async function selectConversation(id: number) {
  activeConversationId.value = id
  messages.value = []
  error.value = ''
  try {
    const list: ConversationMessage[] = await conversationApi.messages(id)
    messages.value = list.map((m) => {
      const meta = (m.metadata ?? {}) as Record<string, unknown>
      return {
        role: m.role,
        content: m.content,
        steps: (meta.steps as AgentStep[] | undefined) ?? [],
        proposals: ((meta.proposals as AgentProposal[] | undefined) ?? []).map((p) => ({
          proposal: p,
          status: 'approved' as const,
        })),
        navigate: (meta.navigate as string | null | undefined) ?? null,
      }
    })
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载会话失败'
  }
}

async function deleteConversation(id: number) {
  error.value = ''
  try {
    await conversationApi.remove(id)
    conversations.value = conversations.value.filter((c) => c.id !== id)
    if (activeConversationId.value === id) {
      activeConversationId.value = null
      messages.value = []
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '删除会话失败'
  }
}

async function send(text?: string) {
  const msg = (text ?? input.value).trim()
  if (!msg || loading.value) return

  error.value = ''
  messages.value.push({ role: 'user', content: msg })
  input.value = ''
  loading.value = true
  await scrollToBottom()

  try {
    const resp = await agentApi.chat(msg, {
      workbookId: workbookId.value,
      conversationId: activeConversationId.value,
      context: context.value,
    })

    if (resp.conversation_id != null) {
      activeConversationId.value = resp.conversation_id
      if (!conversations.value.some((c) => c.id === resp.conversation_id)) {
        conversations.value.unshift({
          id: resp.conversation_id,
          title: null,
          created_at: '',
          updated_at: '',
          last_message: msg,
        })
      }
    }

    if (resp.status === 'failed' || resp.error) {
      error.value = resp.error?.message || 'AI 请求失败，请稍后重试'
    }

    const proposals: ProposalState[] = (resp.proposals ?? []).map((proposal) => ({
      proposal,
      status: 'pending',
    }))

    messages.value.push({
      role: 'assistant',
      content: resp.reply || '已完成。',
      steps: resp.steps ?? [],
      proposals,
      navigate: resp.navigate ?? null,
    })

    if (resp.navigate && resp.navigate.startsWith('/')) {
      await router.push(resp.navigate)
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '请求失败，请稍后重试'
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

async function confirmProposal(
  message: ChatMessage,
  index: number,
  approved: boolean,
) {
  const state = message.proposals?.[index]
  if (!state || state.status !== 'pending') return

  try {
    await agentApi.confirm(state.proposal.proposal_id, approved)
    state.status = approved ? 'approved' : 'rejected'
  } catch (e) {
    error.value = e instanceof Error ? e.message : '确认操作失败'
  }
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault()
    send()
  }
}

onMounted(async () => {
  try {
    workbooks.value = await workbookApi.list()
  } catch {
    // 工作簿列表加载失败不阻塞聊天
  }
  await loadConversations()
})
</script>

<template>
  <div class="mx-auto flex h-[calc(100vh-7rem)] max-w-6xl gap-4 animate-fade-in">
    <!-- 会话侧边栏（#47） -->
    <aside
      class="hidden w-56 shrink-0 flex-col rounded-2xl border border-slate-200/70 bg-white/60 p-3 backdrop-blur dark:border-slate-800 dark:bg-slate-900/50 md:flex"
    >
      <div class="mb-3 flex items-center justify-between gap-2">
        <span class="flex items-center gap-1.5 text-sm font-semibold text-slate-700 dark:text-slate-200">
          <MessageSquare :size="15" class="text-indigo-500" />
          会话
        </span>
        <button class="btn-icon !h-7 !w-7" title="新建会话" @click="createConversation">
          <Plus :size="15" />
        </button>
      </div>

      <div class="flex-1 space-y-1 overflow-y-auto">
        <button
          v-for="c in conversations"
          :key="c.id"
          class="flex w-full items-center gap-1.5 rounded-lg px-2 py-2 text-left text-xs transition"
          :class="
            activeConversationId === c.id
              ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-300'
              : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
          "
          @click="selectConversation(c.id)"
        >
          <MessageSquare :size="13" class="shrink-0" />
          <span class="min-w-0 flex-1 truncate">{{ c.title || `会话 ${c.id}` }}</span>
          <span
            class="shrink-0 rounded p-0.5 text-slate-300 transition hover:text-rose-500 dark:text-slate-600"
            role="button"
            title="删除会话"
            @click.stop="deleteConversation(c.id)"
          >
            <Trash2 :size="12" />
          </span>
        </button>
        <p v-if="conversations.length === 0" class="px-2 py-6 text-center text-xs text-slate-400">
          暂无会话
        </p>
      </div>
    </aside>

    <!-- 聊天主区域 -->
    <div class="flex min-w-0 flex-1 flex-col">
      <!-- 头部：标题 + 练习册选择 -->
      <div class="mb-3 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 class="flex items-center gap-2 text-xl font-bold text-slate-800 dark:text-white">
            <span
              class="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-lg shadow-indigo-500/25"
            >
              <Sparkles :size="18" />
            </span>
            智能助手
          </h1>
          <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">
            对话式任务编排：整理资料、出题、分析薄弱点。写操作会先弹出确认卡片。
          </p>
        </div>

        <select v-model="workbookId" class="input max-w-xs" aria-label="选择练习册">
          <option :value="null">全部练习册</option>
          <option v-for="wb in workbooks" :key="wb.id" :value="wb.id">
            {{ wb.name }}
          </option>
        </select>
      </div>

      <!-- 消息区 -->
      <div
        ref="listEl"
        class="flex-1 space-y-4 overflow-y-auto rounded-2xl border border-slate-200/70 bg-white/60 p-4 backdrop-blur dark:border-slate-800 dark:bg-slate-900/50"
      >
        <!-- 空状态 -->
        <div
          v-if="messages.length === 0 && !loading"
          class="flex h-full flex-col items-center justify-center py-12 text-center"
        >
          <div
            class="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-xl shadow-indigo-500/25"
          >
            <Bot :size="30" />
          </div>
          <h2 class="mt-4 text-lg font-semibold text-slate-800 dark:text-white">
            今天想学点什么？
          </h2>
          <p class="mt-1 max-w-sm text-sm text-slate-500 dark:text-slate-400">
            试着说“把第三章改简单点”或“针对薄弱点出 5 道题”，我会先给方案，确认后再执行。
          </p>
          <div class="mt-5 flex flex-wrap justify-center gap-2">
            <button v-for="s in SUGGESTIONS" :key="s" class="btn-secondary" @click="send(s)">
              {{ s }}
            </button>
          </div>
        </div>

        <!-- 消息流 -->
        <div v-for="(msg, mi) in messages" :key="mi" class="flex flex-col gap-2">
          <!-- 用户消息：右侧气泡 -->
          <div v-if="msg.role === 'user'" class="flex justify-end">
            <div
              class="max-w-[80%] rounded-2xl rounded-br-sm bg-gradient-to-br from-indigo-500 to-purple-600 px-4 py-2.5 text-sm text-white shadow-sm"
            >
              {{ msg.content }}
            </div>
          </div>

          <!-- 助手消息：左侧卡片 -->
          <div v-else class="flex justify-start">
            <div class="w-full max-w-[92%] space-y-2">
              <div class="flex items-start gap-2.5">
                <span
                  class="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 text-white"
                >
                  <Sparkles :size="14" />
                </span>
                <div
                  class="min-w-0 flex-1 rounded-2xl rounded-tl-sm border border-slate-200/80 bg-white px-4 py-3 text-sm text-slate-700 shadow-sm dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                >
                  <MarkdownContent :content="msg.content" />
                </div>
              </div>

              <!-- 执行步骤（steps） -->
              <div
                v-if="msg.steps && msg.steps.length"
                class="ml-9 overflow-hidden rounded-xl border border-slate-200/80 bg-slate-50/80 dark:border-slate-700 dark:bg-slate-900/60"
              >
                <button
                  class="flex w-full items-center justify-between px-3 py-2 text-xs font-semibold text-slate-500 transition hover:bg-slate-100/70 dark:text-slate-400 dark:hover:bg-slate-800/70"
                  @click="msg.stepsOpen = !msg.stepsOpen"
                >
                  <span class="flex items-center gap-1.5">
                    <Navigation :size="13" class="text-indigo-500" />
                    执行步骤 · {{ msg.steps.length }}
                  </span>
                  <ChevronDown
                    :size="15"
                    class="transition-transform"
                    :class="{ 'rotate-180': msg.stepsOpen }"
                  />
                </button>
                <ul
                  v-if="msg.stepsOpen"
                  class="space-y-1.5 border-t border-slate-200/70 px-3 py-2 dark:border-slate-700"
                >
                  <li v-for="(step, si) in msg.steps" :key="si" class="flex items-start gap-2 text-xs">
                    <CircleCheck
                      v-if="stepStatus(step) === 'success'"
                      :size="14"
                      class="mt-0.5 shrink-0 text-emerald-500"
                    />
                    <CircleX v-else :size="14" class="mt-0.5 shrink-0 text-rose-500" />
                    <div class="min-w-0">
                      <span class="font-mono font-semibold text-slate-700 dark:text-slate-200">
                        {{ step.tool }}
                      </span>
                      <span v-if="step.summary" class="ml-2 text-slate-500 dark:text-slate-400">
                        {{ step.summary }}
                      </span>
                      <p v-if="step.error" class="mt-0.5 text-rose-500">{{ step.error }}</p>
                    </div>
                  </li>
                </ul>
              </div>

              <!-- 写操作确认卡片（proposals） -->
              <div v-if="msg.proposals && msg.proposals.length" class="ml-9 space-y-2">
                <div
                  v-for="(state, pi) in msg.proposals"
                  :key="state.proposal.proposal_id"
                  class="rounded-xl border p-3 shadow-sm transition-colors"
                  :class="
                    state.status === 'approved'
                      ? 'border-emerald-200 bg-emerald-50/70 dark:border-emerald-500/30 dark:bg-emerald-500/10'
                      : state.status === 'rejected'
                        ? 'border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-800/50'
                        : 'border-amber-200 bg-amber-50/70 dark:border-amber-500/30 dark:bg-amber-500/10'
                  "
                >
                  <div class="flex items-start justify-between gap-2">
                    <div class="min-w-0">
                      <p class="text-sm font-semibold text-slate-800 dark:text-white">
                        {{ actionLabel(state.proposal.action) }}
                        <span
                          v-if="targetSummary(state.proposal)"
                          class="font-normal text-slate-500 dark:text-slate-400"
                        >
                          · {{ targetSummary(state.proposal) }}
                        </span>
                      </p>
                      <p
                        v-if="state.proposal.impact"
                        class="mt-0.5 text-xs text-slate-500 dark:text-slate-400"
                      >
                        {{ state.proposal.impact }}
                      </p>
                    </div>
                    <span
                      v-if="state.status !== 'pending'"
                      class="badge shrink-0"
                      :class="
                        state.status === 'approved'
                          ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-400'
                          : 'bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-300'
                      "
                    >
                      <Check v-if="state.status === 'approved'" :size="12" />
                      <X v-else :size="12" />
                      {{ state.status === 'approved' ? '已确认' : '已取消' }}
                    </span>
                  </div>

                  <div
                    v-if="
                      changesSummary(state.proposal).before != null ||
                      changesSummary(state.proposal).after != null
                    "
                    class="mt-2 space-y-1.5 text-xs"
                  >
                    <div
                      v-if="changesSummary(state.proposal).before != null"
                      class="rounded-lg bg-white/70 px-3 py-2 text-slate-500 line-through decoration-rose-300 dark:bg-slate-900/50 dark:text-slate-400"
                    >
                      {{ changesSummary(state.proposal).before }}
                    </div>
                    <div
                      v-if="changesSummary(state.proposal).after != null"
                      class="rounded-lg bg-white/70 px-3 py-2 text-slate-700 dark:bg-slate-900/50 dark:text-slate-200"
                    >
                      {{ changesSummary(state.proposal).after }}
                    </div>
                  </div>

                  <div v-if="state.status === 'pending'" class="mt-3 flex justify-end gap-2">
                    <button class="btn-secondary !py-1.5 text-xs" @click="confirmProposal(msg, pi, false)">
                      <X :size="14" />
                      取消
                    </button>
                    <button class="btn-primary !py-1.5 text-xs" @click="confirmProposal(msg, pi, true)">
                      <Check :size="14" />
                      确认执行
                    </button>
                  </div>
                </div>
              </div>

              <!-- navigate 跳转提示 -->
              <div
                v-if="msg.navigate"
                class="ml-9 flex items-center gap-1.5 text-xs text-indigo-500 dark:text-indigo-400"
              >
                <Navigation :size="13" />
                已为你跳转到「{{ msg.navigate }}」
              </div>
            </div>
          </div>
        </div>

        <!-- 加载中 -->
        <div v-if="loading" class="flex items-center gap-2 text-sm text-slate-400">
          <Loader2 :size="16" class="animate-spin text-indigo-500" />
          <span class="flex items-center gap-1">
            <Sparkles :size="13" />
            助手正在思考
          </span>
        </div>

        <!-- 错误 -->
        <p v-if="error" class="text-sm text-rose-500">{{ error }}</p>
      </div>

      <!-- 输入区 -->
      <div class="mt-3 flex items-end gap-2">
        <div class="relative flex-1">
          <textarea
            v-model="input"
            rows="1"
            class="input resize-none pr-10 leading-relaxed"
            placeholder="输入你的问题，Enter 发送，Shift+Enter 换行"
            :disabled="loading"
            @keydown="onKeydown"
          ></textarea>
        </div>
        <button
          class="btn-primary h-11 w-11 !rounded-xl !p-0"
          :disabled="loading || !input.trim()"
          aria-label="发送"
          @click="send()"
        >
          <Loader2 v-if="loading" :size="18" class="animate-spin" />
          <Send v-else :size="18" />
        </button>
      </div>
    </div>
  </div>
</template>
