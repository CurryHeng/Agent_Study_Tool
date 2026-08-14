<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  BookOpen,
  Brain,
  CheckCircle2,
  ChevronRight,
  Clock,
  Layers,
  Network,
  Play,
  Send,
  Sparkles,
  Star,
} from 'lucide-vue-next'
import { agentApi, reviewApi, workbookApi } from '../api'
import { SYSTEM_WORKBOOK_ID } from '../lib/constants'
import type { DueItem, Workbook } from '../types'

const router = useRouter()
const workbooks = ref<Workbook[]>([])
const due = ref<DueItem[]>([])
const favorites = ref<DueItem[]>([])
const newName = ref('')
const agentMessage = ref('')
const agentLoading = ref(false)
const agentResult = ref<{ task_id: string; intent: string; result: Record<string, unknown> } | null>(null)

const builtin: Workbook = {
  id: SYSTEM_WORKBOOK_ID,
  user_id: 0,
  name: '内置题库',
  description: '系统内置参考题库（只读）',
  created_at: '',
  updated_at: '',
}

const allWorkbooks = computed(() => [builtin, ...workbooks.value])

const stats = computed(() => {
  const cards = due.value.map((d) => d.card)
  const reviewed = cards.filter((c) => c.last_review).length
  return { due: due.value.length, reviewed, total: cards.length }
})

const favoriteCount = computed(() => favorites.value.length)

const dueByKnowledge = computed(() => {
  const map = new Map<string, number>()
  for (const d of due.value) {
    const name = d.question.knowledge_name || '未分类'
    map.set(name, (map.get(name) || 0) + 1)
  }
  return [...map.entries()].sort((a, b) => b[1] - a[1])
})

const maxKnowledgeCount = computed(() =>
  dueByKnowledge.value.reduce((m, [, c]) => Math.max(m, c), 1),
)

async function load() {
  workbooks.value = await workbookApi.list()
  due.value = await reviewApi.due()
  favorites.value = await reviewApi.due(20, true)
}

async function createWorkbook() {
  if (!newName.value.trim()) return
  await workbookApi.create(newName.value.trim())
  newName.value = ''
  await load()
}

async function sendAgent() {
  if (!agentMessage.value.trim() || agentLoading.value) return
  agentLoading.value = true
  try {
    agentResult.value = await agentApi.chat(agentMessage.value)
    agentMessage.value = ''
  } finally {
    agentLoading.value = false
  }
}

const agentQuestions = computed(() => {
  const r = agentResult.value?.result
  return (r && Array.isArray(r.questions) ? r.questions : []) as Record<string, unknown>[]
})

onMounted(load)
</script>

<template>
  <div class="space-y-6">
    <!-- Hero -->
    <section class="hero-grad relative overflow-hidden rounded-3xl p-8 text-white shadow-xl shadow-emerald-600/20 animate-slide-up">
      <div class="pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full bg-white/10"></div>
      <div class="pointer-events-none absolute -bottom-16 right-24 h-48 w-48 rounded-full bg-white/5"></div>
      <div class="pointer-events-none absolute right-16 top-6 hidden opacity-20 sm:block">
        <Brain :size="120" />
      </div>

      <p class="text-sm font-medium text-emerald-100">StudyForge · 你的 AI 学习伙伴</p>
      <h1 class="mt-2 text-3xl font-bold tracking-tight">
        {{ stats.due > 0 ? `今天有 ${stats.due} 道题待复习` : '全部搞定！' }}
      </h1>
      <p class="mt-2 max-w-md text-sm text-emerald-100/90">
        {{ stats.due > 0 ? '保持节奏，每天进步一点点。' : '没有待复习的题目，去题库刷几道新的吧。' }}
      </p>
      <button
        class="mt-6 inline-flex items-center gap-2 rounded-xl bg-white px-5 py-2.5 font-semibold text-teal-700 shadow-md transition hover:bg-emerald-50 active:scale-[0.98]"
        @click="router.push('/review')"
      >
        <Play :size="16" class="fill-current" />
        开始刷题
      </button>
    </section>

    <div class="stagger-children space-y-6">
      <!-- 统计 -->
      <section class="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div class="card card-hover flex items-center gap-4 !p-4">
          <span class="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-orange-100 text-orange-600 dark:bg-orange-500/15 dark:text-orange-400">
            <Clock :size="22" />
          </span>
          <div>
            <p class="text-xs font-medium text-slate-500 dark:text-slate-400">待复习</p>
            <p class="text-2xl font-bold text-slate-800 dark:text-white">{{ stats.due }}</p>
          </div>
        </div>
        <div class="card card-hover flex items-center gap-4 !p-4">
          <span class="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-emerald-100 text-emerald-600 dark:bg-emerald-500/15 dark:text-emerald-400">
            <CheckCircle2 :size="22" />
          </span>
          <div>
            <p class="text-xs font-medium text-slate-500 dark:text-slate-400">今日已复习</p>
            <p class="text-2xl font-bold text-slate-800 dark:text-white">{{ stats.reviewed }}</p>
          </div>
        </div>
        <div class="card card-hover flex items-center gap-4 !p-4">
          <span class="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-indigo-100 text-indigo-600 dark:bg-indigo-500/15 dark:text-indigo-400">
            <Layers :size="22" />
          </span>
          <div>
            <p class="text-xs font-medium text-slate-500 dark:text-slate-400">复习卡总数</p>
            <p class="text-2xl font-bold text-slate-800 dark:text-white">{{ stats.total }}</p>
          </div>
        </div>
      </section>

      <!-- 收藏夹 -->
      <button
        v-if="favoriteCount > 0"
        class="card card-hover flex w-full items-center justify-between !py-3 text-left"
        @click="router.push('/review?favorites=1')"
      >
        <div class="flex items-center gap-2.5">
          <Star :size="18" class="fill-amber-400 text-amber-400" />
          <p class="font-medium text-slate-700 dark:text-slate-200">收藏夹</p>
          <span class="badge bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-400">{{ favoriteCount }} 题</span>
        </div>
        <ChevronRight :size="18" class="text-slate-400" />
      </button>

      <!-- 待复习知识点分布 -->
      <section v-if="dueByKnowledge.length > 0" class="card">
        <h3 class="mb-4 flex items-center gap-2 font-semibold text-slate-800 dark:text-white">
          <Brain :size="17" class="text-indigo-500" />
          待复习知识点分布
        </h3>
        <div class="space-y-3">
          <div v-for="[name, count] in dueByKnowledge" :key="name">
            <div class="mb-1 flex items-center justify-between text-sm">
              <span class="text-slate-600 dark:text-slate-300">{{ name }}</span>
              <span class="font-medium text-slate-400">{{ count }} 题</span>
            </div>
            <div class="h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
              <div
                class="progress-bar h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500"
                :style="{ width: `${(count / maxKnowledgeCount) * 100}%` }"
              ></div>
            </div>
          </div>
        </div>
      </section>

      <!-- 题库 -->
      <section>
        <h3 class="mb-3 font-semibold text-slate-800 dark:text-white">题库</h3>
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div
            v-for="wb in allWorkbooks"
            :key="wb.id"
            class="card card-hover"
          >
            <div class="flex items-start justify-between gap-3">
              <div class="flex items-center gap-3">
                <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white">
                  <BookOpen :size="18" />
                </span>
                <div>
                  <p class="font-medium text-slate-700 dark:text-slate-200">{{ wb.name }}</p>
                  <p class="text-xs text-slate-400">{{ wb.description || '练习册' }}</p>
                </div>
              </div>
            </div>
            <div class="mt-4 flex gap-2">
              <button class="btn-secondary flex-1 !py-1.5 text-xs" @click="router.push(`/questions?workbook_id=${wb.id}`)">
                题库
              </button>
              <button class="btn-secondary flex-1 !py-1.5 text-xs" @click="router.push(`/mindmap?workbook_id=${wb.id}`)">
                思维导图
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- 新建练习册 -->
      <section class="card">
        <h3 class="mb-3 flex items-center gap-2 font-semibold text-slate-800 dark:text-white">
          <Network :size="17" class="text-indigo-500" />
          新建练习册
        </h3>
        <div class="flex gap-2">
          <input v-model="newName" class="input" placeholder="练习册名称" @keyup.enter="createWorkbook" />
          <button class="btn-primary shrink-0" @click="createWorkbook">创建</button>
        </div>
      </section>

      <!-- AI 助手 -->
      <section class="card">
        <h3 class="mb-3 flex items-center gap-2 font-semibold text-slate-800 dark:text-white">
          <Sparkles :size="17" class="text-violet-500" />
          AI 助手
        </h3>
        <div class="flex gap-2">
          <input
            v-model="agentMessage"
            class="input"
            placeholder="例如：帮我生成 5 道选择题（需先在 .env 配置 DEEPSEEK_API_KEY）"
            @keyup.enter="sendAgent"
          />
          <button class="btn-primary shrink-0" :disabled="agentLoading" @click="sendAgent">
            <Send :size="15" />
            发送
          </button>
        </div>

        <div v-if="agentResult" class="mt-4 space-y-2 animate-fade-in">
          <template v-if="agentResult.intent === 'generate_questions'">
            <div
              v-for="q in agentQuestions"
              :key="String(q.id)"
              class="rounded-xl border border-slate-200 p-3 text-sm dark:border-slate-700"
            >
              <p class="font-medium text-slate-700 dark:text-slate-200">{{ q.content }}</p>
              <p class="mt-1 text-xs text-slate-500 dark:text-slate-400">答案：{{ q.answer }}</p>
            </div>
          </template>
          <p v-else-if="agentResult.intent === 'generate_mindmap'" class="text-sm text-slate-600 dark:text-slate-300">
            已生成思维导图，可前往「思维导图」查看。
          </p>
          <p v-else-if="agentResult.intent === 'list_documents'" class="text-sm text-slate-600 dark:text-slate-300">
            已为你列出文档。
          </p>
          <p v-else class="text-sm text-slate-600 dark:text-slate-300">
            {{ (agentResult.result && agentResult.result.reply) || '已完成' }}
          </p>
        </div>
      </section>
    </div>
  </div>
</template>
