<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  AlertCircle,
  ArrowLeft,
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Coffee,
  Flame,
  Lightbulb,
  Play,
  Star,
  Timer,
  X,
  XCircle,
} from 'lucide-vue-next'
import { reviewApi } from '../api'
import type { AnswerResult, DueItem } from '../types'
import RatingButtons from '../components/RatingButtons.vue'
import MarkdownContent from '../components/MarkdownContent.vue'
import { gradeQuestion } from '../lib/grading'

type Mode = 'relaxed' | 'normal' | 'strict'

const MODES: { key: Mode; label: string; desc: string; icon: typeof Coffee }[] = [
  { key: 'relaxed', label: '宽松模式', desc: '自由练习，不限时', icon: Coffee },
  { key: 'normal', label: '普通模式', desc: '逐题计时评分', icon: Timer },
  { key: 'strict', label: '严格模式', desc: '模拟考试，答完即判', icon: Flame },
]

const route = useRoute()
const router = useRouter()
const favoritesOnly = route.query.favorites === '1'

const mode = ref<Mode>('relaxed')
const due = ref<DueItem[]>([])
const index = ref(0)
const started = ref(false)
const loading = ref(false)
const error = ref('')
const finished = ref(false)

// 当前题作答状态
const selected = ref<string | null>(null)
const textAnswer = ref('')
const revealed = ref(false) // 填空/简答已揭晓答案
const selfAssessed = ref<boolean | null>(null) // 揭晓后自评
const pendingRating = ref<string | null>(null) // 选了 again/hard 等待填错因
const result = ref<AnswerResult | null>(null)
const wrongReasonInput = ref('')
const wrongAnswerInput = ref('')

const results = ref<(boolean | null)[]>([])
const remaining = ref(300)
let timer: ReturnType<typeof setInterval> | null = null

const SESSION_KEY = 'studyforge-quiz-session-last'

interface SessionSnapshot {
  mode: Mode
  index: number
  total: number
  results: (boolean | null)[]
  current: {
    selected: string | null
    textAnswer: string
    revealed: boolean
    selfAssessed: boolean | null
    pendingRating: string | null
    result: AnswerResult | null
    wrongReasonInput: string
    wrongAnswerInput: string
    remaining: number
  } | null
}

const resume = ref<SessionSnapshot | null>(null)

const current = computed(() => due.value[index.value])
const isChoice = computed(() => (current.value?.question.options.length ?? 0) > 0)
const currentMode = computed(() => MODES.find((m) => m.key === mode.value)!)
const rated = computed(() => result.value != null)
const progress = computed(() =>
  due.value.length ? Math.round((results.value.filter((r) => r !== null).length / due.value.length) * 100) : 0,
)
const allRated = computed(
  () => due.value.length > 0 && results.value.filter((r) => r !== null).length >= due.value.length,
)

const localCorrect = computed(() => {
  const q = current.value?.question
  if (!q || !isChoice.value || selected.value == null) return null
  return gradeQuestion(q, selected.value)
})

// 允许的评分项（按对错过滤，避免"答错却评简单"）
const allowedRatings = computed<string[] | undefined>(() => {
  if (rated.value || mode.value === 'strict') return undefined
  if (isChoice.value) {
    if (localCorrect.value === true) return ['good', 'easy']
    if (localCorrect.value === false) return ['again', 'hard']
    return undefined
  }
  if (!revealed.value) return undefined
  if (selfAssessed.value === true) return ['good', 'easy']
  if (selfAssessed.value === false) return ['again', 'hard']
  return undefined
})

const canRate = computed(() => {
  if (rated.value || mode.value === 'strict') return false
  if (isChoice.value) return localCorrect.value != null
  return revealed.value && selfAssessed.value != null
})

const correctCount = computed(() => results.value.filter((r) => r === true).length)
const rate = computed(() =>
  results.value.length ? Math.round((correctCount.value / results.value.filter((r) => r !== null).length) * 100) : 0,
)

function saveSession() {
  if (!started.value || finished.value) return
  const snapshot: SessionSnapshot = {
    mode: mode.value,
    index: index.value,
    total: due.value.length,
    results: [...results.value],
    current: {
      selected: selected.value,
      textAnswer: textAnswer.value,
      revealed: revealed.value,
      selfAssessed: selfAssessed.value,
      pendingRating: pendingRating.value,
      result: result.value,
      wrongReasonInput: wrongReasonInput.value,
      wrongAnswerInput: wrongAnswerInput.value,
      remaining: remaining.value,
    },
  }
  localStorage.setItem(SESSION_KEY, JSON.stringify(snapshot))
}

async function start() {
  loading.value = true
  error.value = ''
  try {
    due.value = await reviewApi.due(20, favoritesOnly)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载复习题失败，请稍后重试'
    return
  } finally {
    loading.value = false
  }
  started.value = true

  if (
    resume.value &&
    resume.value.mode === mode.value &&
    resume.value.index >= 0 &&
    resume.value.index < due.value.length
  ) {
    index.value = resume.value.index
    results.value = resume.value.results && resume.value.results.length === due.value.length
      ? [...resume.value.results]
      : new Array(due.value.length).fill(null)
    const cur = resume.value.current
    if (cur) {
      selected.value = cur.selected
      textAnswer.value = cur.textAnswer ?? ''
      revealed.value = cur.revealed ?? false
      selfAssessed.value = cur.selfAssessed ?? null
      pendingRating.value = cur.pendingRating ?? null
      result.value = cur.result ?? null
      wrongReasonInput.value = cur.wrongReasonInput ?? ''
      wrongAnswerInput.value = cur.wrongAnswerInput ?? ''
      remaining.value = cur.remaining ?? 300
      startTimer()
    } else {
      resetCard()
    }
    resume.value = null
  } else {
    localStorage.removeItem(SESSION_KEY)
    results.value = new Array(due.value.length).fill(null)
    resetCard()
  }
  saveSession()
}

function pickResume() {
  mode.value = resume.value?.mode || 'relaxed'
  start()
}

function discardResume() {
  resume.value = null
  localStorage.removeItem(SESSION_KEY)
}

function checkResume() {
  try {
    const raw = localStorage.getItem(SESSION_KEY)
    if (!raw) return
    const s = JSON.parse(raw)
    if (
      s &&
      (s.mode === 'relaxed' || s.mode === 'normal' || s.mode === 'strict') &&
      typeof s.index === 'number' &&
      typeof s.total === 'number' &&
      Array.isArray(s.results)
    ) {
      resume.value = s as SessionSnapshot
    }
  } catch {
    resume.value = null
  }
}

async function toggleFavorite() {
  const q = current.value.question
  const card = await reviewApi.favorite(q.id)
  due.value[index.value].card = card
}

function resetCard() {
  selected.value = null
  textAnswer.value = ''
  revealed.value = false
  selfAssessed.value = null
  pendingRating.value = null
  result.value = null
  wrongReasonInput.value = ''
  wrongAnswerInput.value = ''
  remaining.value = 300
  startTimer()
}

function startTimer() {
  stopTimer()
  if (mode.value !== 'normal') return
  timer = setInterval(() => {
    remaining.value = Math.max(0, remaining.value - 1)
  }, 1000)
}

function stopTimer() {
  if (timer) clearInterval(timer)
  timer = null
}

function choose(optionKey: string) {
  if (rated.value) return
  selected.value = optionKey
  if (mode.value === 'strict') submit()
}

async function submit(rating?: string, wrongReason?: string) {
  if (rated.value) return
  stopTimer()
  const q = current.value.question
  const answer = isChoice.value ? selected.value : textAnswer.value
  const r = await reviewApi.answer(q.id, {
    user_answer: answer,
    mode: mode.value,
    ...(rating ? { rating } : {}),
    ...(wrongReason ? { wrong_reason: wrongReason } : {}),
  })
  result.value = r
  const ok = r.is_correct === null ? r.rating === 'good' || r.rating === 'easy' : r.is_correct
  results.value[index.value] = ok
}

function onRate(rating: string) {
  if (rating === 'again' || rating === 'hard') {
    pendingRating.value = rating
  } else {
    submit(rating)
  }
}

function saveWrongRecord() {
  submit(pendingRating.value || 'again', wrongReasonInput.value.trim())
  pendingRating.value = null
}

function skipWrong() {
  submit(pendingRating.value || 'again')
  pendingRating.value = null
}

function next() {
  if (index.value < due.value.length - 1) {
    index.value++
    resetCard()
    saveSession()
  } else {
    finished.value = true
    localStorage.removeItem(SESSION_KEY)
  }
}

function prev() {
  if (index.value > 0) {
    index.value--
    resetCard()
    saveSession()
  }
}

function restart() {
  index.value = 0
  finished.value = false
  localStorage.removeItem(SESSION_KEY)
  results.value = new Array(due.value.length).fill(null)
  resetCard()
}

watch(mode, () => resetCard())
watch(
  () => [
    mode.value,
    index.value,
    started.value,
    finished.value,
    selected.value,
    textAnswer.value,
    revealed.value,
    selfAssessed.value,
    pendingRating.value,
    result.value,
    wrongReasonInput.value,
    wrongAnswerInput.value,
    remaining.value,
    [...results.value],
  ],
  saveSession,
  { deep: true },
)
onMounted(checkResume)
onBeforeUnmount(stopTimer)
</script>

<template>
  <div>
    <!-- 模式选择 / 会话续答 -->
    <template v-if="!started">
      <div v-if="resume" class="card mb-4 border-emerald-200 bg-emerald-50/60 dark:border-emerald-500/30 dark:bg-emerald-500/10 animate-slide-up">
        <p class="text-sm font-medium text-emerald-700 dark:text-emerald-300">
          检测到未完成的刷题会话（第 {{ resume.index + 1 }} / {{ resume.total }} 题）
        </p>
        <div class="mt-3 flex gap-2">
          <button class="btn-primary !py-1.5 text-xs" @click="pickResume">继续刷题</button>
          <button class="btn-ghost !py-1.5 text-xs" @click="discardResume">放弃</button>
        </div>
      </div>

      <div class="card space-y-4">
        <p class="text-sm text-slate-500 dark:text-slate-400">选择复习模式（本轮不可切换）</p>
        <p v-if="error" class="text-sm text-rose-500">{{ error }}</p>
        <div class="space-y-2">
          <button
            v-for="m in MODES"
            :key="m.key"
            class="flex w-full items-center gap-3 rounded-xl border-2 p-4 text-left transition"
            :class="
              mode === m.key
                ? 'border-emerald-500 bg-emerald-50 dark:border-emerald-500 dark:bg-emerald-500/10'
                : 'border-slate-200 hover:border-emerald-300 dark:border-slate-700 dark:hover:border-emerald-600'
            "
            @click="mode = m.key"
          >
            <span
              class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg"
              :class="mode === m.key ? 'bg-emerald-600 text-white' : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'"
            >
              <component :is="m.icon" :size="18" />
            </span>
            <div>
              <p class="font-semibold text-slate-800 dark:text-white">{{ m.label }}</p>
              <p class="text-xs text-slate-500 dark:text-slate-400">{{ m.desc }}</p>
            </div>
          </button>
        </div>
        <button class="btn-primary w-full" :disabled="loading" @click="start">
          {{ loading ? '加载中…' : '开始' }}
        </button>
      </div>
    </template>

    <!-- 结果页 -->
    <div v-else-if="finished" class="space-y-5 animate-fade-in">
      <div class="card py-8 text-center">
        <div
          class="mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 text-3xl shadow-lg shadow-emerald-500/25"
        >
          <span>{{ rate >= 80 ? '🎉' : rate >= 50 ? '📚' : '💪' }}</span>
        </div>
        <h2 class="mb-2 text-xl font-bold text-slate-800 dark:text-white">本轮复习完成！</h2>
        <p class="mb-6 text-sm text-slate-500 dark:text-slate-400">
          共复习 {{ due.length }} 道题，掌握率 {{ rate }}%
        </p>

        <div class="relative mx-auto mb-6 h-24 w-24">
          <svg viewBox="0 0 36 36" class="h-full w-full -rotate-90">
            <circle cx="18" cy="18" r="15.9" fill="none" stroke="#e2e8f0" stroke-width="3" />
            <circle
              cx="18" cy="18" r="15.9" fill="none" stroke="#10b981" stroke-width="3"
              stroke-linecap="round" :stroke-dasharray="`${rate} ${100 - rate}`"
            />
          </svg>
          <span class="absolute inset-0 flex items-center justify-center text-lg font-bold text-slate-700 dark:text-white">
            {{ rate }}%
          </span>
        </div>

        <div class="flex justify-center gap-4 text-sm">
          <div class="flex items-center gap-1.5">
            <CheckCircle2 :size="16" class="text-emerald-500" />
            <span class="text-slate-600 dark:text-slate-300">掌握 {{ correctCount }}</span>
          </div>
          <div class="flex items-center gap-1.5">
            <XCircle :size="16" class="text-rose-400" />
            <span class="text-slate-600 dark:text-slate-300">需复习 {{ results.filter((r) => r === false).length }}</span>
          </div>
        </div>
      </div>

      <div class="flex gap-3">
        <button class="btn-primary flex-1" @click="restart">再来一轮</button>
        <button class="btn-secondary flex-1" @click="router.push('/')">返回首页</button>
      </div>
    </div>

    <!-- 答题中 -->
    <div v-else-if="current" class="space-y-4 animate-fade-in">
      <!-- 顶部进度条 -->
      <div class="flex items-center gap-3">
        <button class="btn-icon" title="返回" @click="router.push('/')">
          <ArrowLeft :size="18" />
        </button>
        <div class="progress-bar h-2 flex-1 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
          <div
            class="h-full rounded-full bg-gradient-to-r from-emerald-500 to-teal-500 transition-all duration-700"
            :style="{ width: `${progress}%` }"
          ></div>
        </div>
        <span class="w-16 text-right text-xs tabular-nums text-slate-400">
          {{ results.filter((r) => r !== null).length }}/{{ due.length }}
        </span>
      </div>

      <!-- 徽标行 -->
      <div class="flex flex-wrap items-center gap-2">
        <span v-if="current.question.knowledge_name" class="badge bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-400">
          {{ current.question.knowledge_name }}
        </span>
        <span
          class="ml-auto badge"
          :class="
            mode === 'strict'
              ? 'bg-rose-50 text-rose-600 dark:bg-rose-500/15 dark:text-rose-400'
              : mode === 'normal'
                ? 'bg-amber-50 text-amber-600 dark:bg-amber-500/15 dark:text-amber-400'
                : 'bg-indigo-50 text-indigo-600 dark:bg-indigo-500/15 dark:text-indigo-300'
          "
        >
          {{ currentMode.label }}
        </span>
        <span v-if="favoritesOnly" class="badge bg-amber-50 text-amber-600 dark:bg-amber-500/15 dark:text-amber-400">收藏夹</span>
        <span v-if="rated" class="badge bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400">已评级</span>
        <button class="btn-icon" :title="current.card.favorited ? '取消收藏' : '收藏'" @click="toggleFavorite">
          <Star :size="19" :class="current.card.favorited ? 'fill-amber-400 text-amber-400' : 'text-slate-300 dark:text-slate-600'" />
        </button>
      </div>

      <!-- 题目卡片 -->
      <div class="card">
        <div class="mb-4 text-[15px] leading-loose text-slate-800 dark:text-slate-100">
          <MarkdownContent :content="current.question.content" />
        </div>

        <!-- 选择题 -->
        <template v-if="isChoice">
          <div class="space-y-2">
            <button
              v-for="o in current.question.options"
              :key="o.id"
              class="flex w-full items-center gap-3 rounded-xl border-2 px-4 py-3 text-left text-sm transition dark:bg-slate-800"
              :class="
                result && o.option_key === current.question.answer
                  ? 'border-emerald-400 bg-emerald-50 dark:border-emerald-500 dark:bg-emerald-500/15'
                  : result && o.option_key === selected
                    ? 'border-rose-400 bg-rose-50 dark:border-rose-500 dark:bg-rose-500/15'
                    : !result && selected === o.option_key
                      ? 'border-emerald-400 bg-emerald-50 dark:border-emerald-500 dark:bg-emerald-500/15'
                      : 'border-slate-200 hover:border-emerald-300 hover:bg-emerald-50/40 dark:border-slate-700 dark:hover:border-emerald-600 dark:hover:bg-slate-700/40'
              "
              :disabled="result != null"
              @click="choose(o.option_key)"
            >
              <span
                class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold"
                :class="
                  result && o.option_key === current.question.answer
                    ? 'bg-emerald-500 text-white'
                    : result && o.option_key === selected
                      ? 'bg-rose-500 text-white'
                      : 'bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-300'
                "
              >
                {{ o.option_key }}
              </span>
              <span class="leading-relaxed">{{ o.content }}</span>
              <span v-if="result && o.option_key === current.question.answer" class="ml-auto shrink-0">
                <Check :size="16" class="text-emerald-500" />
              </span>
              <span v-else-if="result && o.option_key === selected" class="ml-auto shrink-0">
                <X :size="16" class="text-rose-400" />
              </span>
            </button>
          </div>
        </template>

        <!-- 填空/简答 -->
        <template v-else>
          <input v-model="textAnswer" class="input mb-3" placeholder="填写答案" :disabled="revealed || rated" />
          <button v-if="!revealed && !rated" class="btn-primary w-full" @click="revealed = true">揭晓答案</button>
        </template>

        <!-- 已揭晓答案 -->
        <div v-if="revealed && !isChoice" class="mt-4 space-y-3 animate-slide-up">
          <p class="text-sm font-medium text-emerald-600 dark:text-emerald-400">
            正确答案：{{ current.question.answer }}
          </p>
          <div v-if="current.question.analysis" class="rounded-xl bg-slate-50 p-3 dark:bg-slate-800/60">
            <MarkdownContent :content="current.question.analysis" />
          </div>
          <div v-if="selfAssessed === null" class="flex gap-3">
            <button class="btn-secondary flex-1" @click="selfAssessed = true">我做对了</button>
            <button class="btn-danger flex-1" @click="selfAssessed = false">我做错了</button>
          </div>
        </div>

        <!-- 结果反馈 -->
        <div v-if="result" class="mt-4 animate-fade-in">
          <p
            class="flex items-center gap-1.5 text-sm font-medium"
            :class="result.is_correct ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-500 dark:text-rose-400'"
          >
            <CheckCircle2 v-if="result.is_correct" :size="16" />
            <XCircle v-else-if="result.is_correct === false" :size="16" />
            {{ result.is_correct === null ? '已记录' : result.is_correct ? '回答正确' : '回答错误' }}
            <span v-if="isChoice" class="text-slate-400">（正确答案：{{ result.correct_answer }}）</span>
          </p>
          <div v-if="result.analysis" class="mt-2 rounded-xl bg-slate-50 p-3 dark:bg-slate-800/60">
            <MarkdownContent :content="result.analysis" />
          </div>
        </div>
      </div>

      <!-- 计时 -->
      <div v-if="mode === 'normal' && !rated" class="flex items-center gap-2">
        <div class="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
          <div
            class="h-full rounded-full transition-all duration-1000"
            :class="remaining < 60 ? 'bg-rose-500' : 'bg-emerald-500'"
            :style="{ width: `${(remaining / 300) * 100}%` }"
          ></div>
        </div>
        <span :class="`font-mono text-xs font-medium ${remaining < 60 ? 'text-rose-500' : 'text-slate-500'}`">
          {{ Math.floor(remaining / 60) }}:{{ String(remaining % 60).padStart(2, '0') }}
        </span>
      </div>

      <!-- 评分（宽松/普通，未提交时） -->
      <div v-if="canRate && !rated" class="card">
        <RatingButtons :allowed="allowedRatings" :next-review="current.card.due" @rate="onRate" />
      </div>

      <!-- 错因表单（选了 again/hard） -->
      <div v-if="pendingRating" class="card border-orange-200 bg-orange-50/60 dark:border-orange-500/30 dark:bg-orange-500/10 animate-slide-up">
        <p class="mb-3 flex items-center gap-2 text-sm font-semibold text-orange-700 dark:text-orange-300">
          <AlertCircle :size="16" />
          记录错因（可选）
        </p>
        <textarea
          v-model="wrongAnswerInput"
          rows="2"
          class="input mb-2"
          placeholder="你的错误答案或过程…"
        ></textarea>
        <textarea
          v-model="wrongReasonInput"
          rows="2"
          class="input"
          placeholder="为什么做错了…"
        ></textarea>
        <div class="mt-3 flex gap-2">
          <button class="btn-primary !py-1.5 text-xs" @click="saveWrongRecord">保存</button>
          <button class="btn-ghost !py-1.5 text-xs" @click="skipWrong">跳过</button>
        </div>
      </div>

      <!-- 已评级提示 -->
      <div v-if="rated" class="flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-slate-50 py-3 dark:border-slate-700 dark:bg-slate-800 animate-slide-up">
        <Check :size="16" class="text-emerald-500" />
        <span class="text-sm font-medium text-slate-600 dark:text-slate-300">已记录掌握程度</span>
      </div>

      <!-- 一句话总结 -->
      <div v-if="rated && current.question.summary" class="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-500/30 dark:bg-amber-500/10">
        <Lightbulb :size="17" class="mt-0.5 shrink-0 text-amber-500" />
        <div>
          <span class="text-[11px] font-semibold uppercase tracking-wider text-amber-700 dark:text-amber-400">一句话总结</span>
          <MarkdownContent :content="current.question.summary" />
        </div>
      </div>

      <!-- 导航 -->
      <div class="flex items-center gap-3">
        <button class="btn-secondary flex-1" :disabled="index === 0" @click="prev">
          <ChevronLeft :size="16" /> 上一题
        </button>
        <button class="btn-secondary flex-1" :disabled="index >= due.length - 1" @click="next">
          下一题 <ChevronRight :size="16" />
        </button>
      </div>

      <!-- 完成 -->
      <button v-if="allRated && !finished" class="btn-primary w-full" @click="finished = true">
        <Play :size="15" class="fill-current" />
        完成复习，查看结果
      </button>
    </div>

    <!-- 空状态：没有待复习题目 -->
    <div v-else class="card py-12 text-center animate-fade-in">
      <p class="text-sm text-slate-400 dark:text-slate-500">
        暂无待复习的题目。去题库看看，或先导入资料生成题目。
      </p>
      <button class="btn-primary mt-4" @click="started = false">返回模式选择</button>
    </div>
  </div>
</template>
