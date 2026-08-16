<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Check,
  ChevronRight,
  CircleCheck,
  CircleX,
  Library,
  Loader2,
  Pencil,
  Plus,
  Play,
  Search,
  Sparkles,
  Trash2,
  Wand2,
  X,
} from 'lucide-vue-next'
import { knowledgeApi, questionApi, workbookApi } from '../api'
import { SYSTEM_WORKBOOK_ID } from '../lib/constants'
import type { GenerateResult, Knowledge, Question, SimilarQuestion, Workbook } from '../types'
import MarkdownContent from '../components/MarkdownContent.vue'

const route = useRoute()
const router = useRouter()
const workbooks = ref<Workbook[]>([])
const selected = ref<number>(SYSTEM_WORKBOOK_ID)
const questions = ref<Question[]>([])
const similarMap = ref<Record<number, SimilarQuestion>>({})
const loadingSimilar = ref<number | null>(null)

const search = ref('')
const expanded = ref<string | null>(null)
const editMode = ref(false)
const selectedIds = ref<Set<number>>(new Set())

const TYPE_LABEL: Record<string, string> = {
  single_choice: '单选题',
  multiple_choice: '多选题',
  true_false: '判断题',
  fill_blank: '填空题',
  short_answer: '简答题',
}

const showGenerate = ref(false)
const knowledge = ref<Knowledge[]>([])
const genKnowledgeId = ref<number | null>(null)
const genType = ref('single_choice')
const genCount = ref(5)
const genDifficulty = ref(1)
const genLoading = ref(false)
const genError = ref('')
const genResult = ref<GenerateResult | null>(null)

const builtin: Workbook = {
  id: SYSTEM_WORKBOOK_ID,
  user_id: 0,
  name: '内置题库',
  description: '系统内置参考题库（只读）',
  created_at: '',
  updated_at: '',
}
const allWorkbooks = computed(() => [builtin, ...workbooks.value])

const byWorkbook = computed(() => {
  const counts = new Map<number, number>()
  for (const q of questions.value) counts.set(q.workbook_id, (counts.get(q.workbook_id) || 0) + 1)
  return counts
})

const isBuiltin = computed(() => selected.value === SYSTEM_WORKBOOK_ID)

const filtered = computed(() => {
  let qs = questions.value
  if (selected.value !== SYSTEM_WORKBOOK_ID) qs = qs.filter((q) => q.workbook_id === selected.value)
  if (search.value.trim()) {
    const s = search.value.trim()
    qs = qs.filter(
      (q) =>
        q.content.includes(s) ||
        q.answer.includes(s) ||
        (q.knowledge_name || '').includes(s) ||
        (q.analysis || '').includes(s),
    )
  }
  return qs
})

// 按知识点分组（无知识点归 "未分类"）
const grouped = computed(() => {
  const map = new Map<string, Question[]>()
  for (const q of filtered.value) {
    const key = q.knowledge_name || '未分类'
    if (!map.has(key)) map.set(key, [])
    map.get(key)!.push(q)
  }
  return [...map.entries()].sort((a, b) => a[0].localeCompare(b[0], 'zh'))
})

async function load() {
  workbooks.value = await workbookApi.list()
  const fromQuery = route.query.workbook_id
  if (fromQuery != null) selected.value = Number(fromQuery)
  await loadQuestions()
}

async function loadQuestions() {
  questions.value = await questionApi.list()
  similarMap.value = {}
  selectedIds.value = new Set()
}

function toggleSelect(id: number) {
  const next = new Set(selectedIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selectedIds.value = next
}

function groupSelect(key: string) {
  const deletable = (grouped.value.find(([k]) => k === key)?.[1] || []).filter((q) => q.source !== 'builtin')
  const next = new Set(selectedIds.value)
  const allSel = deletable.every((q) => next.has(q.id))
  for (const q of deletable) {
    if (allSel) next.delete(q.id)
    else next.add(q.id)
  }
  selectedIds.value = next
}

function toggleEditMode() {
  editMode.value = !editMode.value
  selectedIds.value = new Set()
  expanded.value = null
}

async function batchDelete() {
  const n = selectedIds.value.size
  if (n === 0) return
  if (!confirm(`确定删除选中的 ${n} 道题目？此操作不可撤销。`)) return
  for (const id of selectedIds.value) await questionApi.remove(id)
  await loadQuestions()
}

async function remove(q: Question) {
  if (!confirm(`确定删除题目「${q.content.slice(0, 30)}…」？`)) return
  await questionApi.remove(q.id)
  await loadQuestions()
}

async function generateSimilar(q: Question) {
  loadingSimilar.value = q.id
  try {
    similarMap.value[q.id] = await questionApi.similar(q.id)
  } catch (e) {
    alert(e instanceof Error ? e.message : '生成失败，请确认已在 backend/.env 配置 DEEPSEEK_API_KEY')
  } finally {
    loadingSimilar.value = null
  }
}

async function saveSimilar(q: Question) {
  const s = similarMap.value[q.id]
  if (!s) return
  const target = q.workbook_id !== SYSTEM_WORKBOOK_ID ? q.workbook_id : workbooks.value[0]?.id
  if (target == null) {
    alert('请先创建一个练习册，才能收藏题目')
    return
  }
  await questionApi.create({
    workbook_id: target,
    type: s.type,
    content: s.content,
    answer: s.answer,
    analysis: s.analysis || null,
    difficulty: s.difficulty,
    ...(s.options.length ? { options: s.options } : {}),
  })
  delete similarMap.value[q.id]
  await loadQuestions()
}

async function openGenerate() {
  showGenerate.value = !showGenerate.value
  if (showGenerate.value && knowledge.value.length === 0) {
    try {
      knowledge.value = await knowledgeApi.list(selected.value)
    } catch {
      knowledge.value = []
    }
  }
}

async function runGenerate() {
  genLoading.value = true
  genError.value = ''
  genResult.value = null
  try {
    genResult.value = await questionApi.generate({
      workbook_id: selected.value,
      knowledge_id: genKnowledgeId.value,
      type: genType.value,
      count: genCount.value,
      difficulty: genDifficulty.value,
    })
    await loadQuestions()
  } catch (e) {
    genError.value =
      e instanceof Error ? e.message : '生成失败，请确认已在 backend/.env 配置 DEEPSEEK_API_KEY'
  } finally {
    genLoading.value = false
  }
}

watch(selected, () => {
  expanded.value = null
  selectedIds.value = new Set()
  showGenerate.value = false
  genResult.value = null
  genKnowledgeId.value = null
  knowledge.value = []
  loadQuestions()
})
onMounted(load)
</script>

<template>
  <div class="space-y-4 animate-fade-in">
    <div class="flex items-center justify-between">
      <h2 class="flex items-center gap-2 text-xl font-bold text-slate-800 dark:text-white">
        <Library :size="20" class="text-emerald-500" />
        题库
      </h2>
      <button
        class="btn-secondary !py-1.5 text-xs"
        :class="editMode ? '!bg-rose-100 !text-rose-700 dark:!bg-rose-500/20 dark:!text-rose-400' : ''"
        @click="toggleEditMode"
      >
        {{ editMode ? '取消' : '编辑' }}
      </button>
    </div>

    <!-- 搜索 -->
    <div class="relative">
      <Search :size="16" class="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
      <input v-model="search" class="input !pl-10" placeholder="搜索题目内容、答案、知识点、解析…" @input="expanded = null" />
    </div>

    <!-- 工作簿 tab -->
    <div class="flex items-center gap-1.5 overflow-x-auto pb-1">
      <button
        v-for="wb in allWorkbooks"
        :key="wb.id"
        class="whitespace-nowrap rounded-full px-3 py-1.5 text-xs transition-all"
        :class="
          selected === wb.id
            ? 'bg-emerald-600 font-medium text-white'
            : 'bg-slate-100 text-slate-500 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-400'
        "
        @click="selected = wb.id"
      >
        {{ wb.name }} ({{ byWorkbook.get(wb.id) || 0 }})
      </button>
      <div v-if="!isBuiltin" class="ml-auto flex shrink-0 gap-1.5">
        <button class="btn-secondary !py-1.5 text-xs" @click="openGenerate">
          <Wand2 :size="13" /> AI 生成
        </button>
        <button class="btn-primary !py-1.5 text-xs" @click="router.push('/questions/add')">
          <Plus :size="13" /> 添加
        </button>
      </div>
    </div>

    <!-- 操作行 -->
    <div class="flex items-center justify-between">
      <p class="text-xs text-slate-400">共 {{ filtered.length }} 道题</p>
      <button v-if="editMode && selectedIds.size > 0" class="btn-danger !py-1.5 text-xs" @click="batchDelete">
        <Trash2 :size="13" /> 删除选中 ({{ selectedIds.size }})
      </button>
      <button v-else class="btn-primary !py-1.5 text-xs" @click="router.push('/review')">
        <Play :size="13" class="fill-current" /> 开始刷题
      </button>
    </div>

    <!-- AI 生成题目 -->
    <div v-if="showGenerate" class="card space-y-4 animate-fade-in">
      <div class="flex items-center justify-between">
        <h3 class="flex items-center gap-2 text-sm font-semibold text-slate-800 dark:text-white">
          <Wand2 :size="16" class="text-violet-500" /> AI 生成题目
        </h3>
        <button class="btn-icon" title="关闭" @click="showGenerate = false">
          <X :size="14" />
        </button>
      </div>

      <div class="grid grid-cols-2 gap-4 md:grid-cols-4">
        <div>
          <label class="label">知识点</label>
          <select v-model="genKnowledgeId" class="input">
            <option :value="null">整体</option>
            <option v-for="k in knowledge" :key="k.id" :value="k.id">{{ k.name }}</option>
          </select>
        </div>
        <div>
          <label class="label">题型</label>
          <select v-model="genType" class="input">
            <option v-for="(label, key) in TYPE_LABEL" :key="key" :value="key">{{ label }}</option>
          </select>
        </div>
        <div>
          <label class="label">数量（1-20）</label>
          <input v-model.number="genCount" type="number" min="1" max="20" class="input" />
        </div>
        <div>
          <label class="label">难度（1-5）</label>
          <input v-model.number="genDifficulty" type="number" min="1" max="5" class="input" />
        </div>
      </div>

      <div class="flex items-center gap-2">
        <button class="btn-primary !py-1.5 text-xs" :disabled="genLoading" @click="runGenerate">
          <Loader2 v-if="genLoading" :size="14" class="animate-spin" />
          <Wand2 v-else :size="14" />
          {{ genLoading ? '生成中…' : '生成' }}
        </button>
        <p v-if="genError" class="text-sm text-rose-500">{{ genError }}</p>
      </div>

      <!-- 审题结果 -->
      <div v-if="genResult" class="space-y-3 border-t border-slate-100 pt-3 dark:border-slate-800">
        <div class="flex items-center gap-4 text-sm">
          <span class="flex items-center gap-1 font-medium text-emerald-600 dark:text-emerald-400">
            <CircleCheck :size="15" /> 通过 {{ genResult.saved.length }} 道
          </span>
          <span class="flex items-center gap-1 font-medium text-rose-500">
            <CircleX :size="15" /> 驳回 {{ genResult.rejected.length }} 道
          </span>
        </div>

        <div v-if="genResult.rejected.length" class="space-y-2">
          <div
            v-for="(item, i) in genResult.rejected"
            :key="i"
            class="rounded-lg border border-rose-200 bg-rose-50/50 p-3 dark:border-rose-500/30 dark:bg-rose-500/10"
          >
            <p class="text-xs font-medium text-slate-700 dark:text-slate-200">{{ item.question.content }}</p>
            <ul class="mt-1 space-y-0.5">
              <li v-for="(issue, j) in item.review.issues" :key="j" class="text-xs text-rose-500">· {{ issue }}</li>
            </ul>
          </div>
        </div>
        <p v-else class="text-xs text-slate-400">全部通过，无驳回。</p>
      </div>
    </div>

    <p v-if="filtered.length === 0" class="card py-12 text-center text-sm text-slate-400 dark:text-slate-500">
      没有找到匹配的题目。
    </p>

    <!-- 知识点分组 -->
    <div class="space-y-3">
      <div v-for="[key, qs] in grouped" :key="key" class="card !p-0 overflow-hidden">
        <button class="flex w-full items-center gap-3 px-5 py-3 text-left transition hover:bg-slate-50 dark:hover:bg-slate-800/50" @click="expanded = expanded === key ? null : key">
          <span
            v-if="editMode"
            class="flex h-5 w-5 shrink-0 items-center justify-center rounded border-2 transition"
            :class="
              qs.filter((q) => q.source !== 'builtin').length > 0 &&
              qs.filter((q) => q.source !== 'builtin').every((q) => selectedIds.has(q.id))
                ? 'border-emerald-500 bg-emerald-500'
                : 'border-slate-300 dark:border-slate-600'
            "
            @click.stop="groupSelect(key)"
          >
            <Check
              v-if="qs.filter((q) => q.source !== 'builtin').length > 0 && qs.filter((q) => q.source !== 'builtin').every((q) => selectedIds.has(q.id))"
              :size="12"
              class="text-white"
            />
          </span>
          <div class="min-w-0 flex-1">
            <p class="truncate text-sm font-semibold text-slate-800 dark:text-white">{{ key }}</p>
            <p class="text-xs text-slate-400">{{ qs.length }} 道题</p>
          </div>
          <ChevronRight :size="16" class="shrink-0 text-slate-300 transition-transform" :class="expanded === key ? 'rotate-90' : ''" />
        </button>

        <div v-if="expanded === key" class="divide-y divide-slate-100 border-t border-slate-100 dark:divide-slate-800 dark:border-slate-800 animate-slide-up">
          <div v-for="q in qs" :key="q.id" class="flex items-start gap-3 px-5 py-3 transition hover:bg-emerald-50/40 dark:hover:bg-slate-800/40">
            <input
              v-if="editMode"
              type="checkbox"
              class="mt-1 shrink-0 accent-emerald-600"
              :disabled="q.source === 'builtin'"
              :checked="selectedIds.has(q.id)"
              @change="toggleSelect(q.id)"
            />
            <div class="min-w-0 flex-1">
              <div class="mb-1 flex flex-wrap items-center gap-2">
                <span
                  class="rounded-full px-1.5 py-0.5 text-[10px] font-medium"
                  :class="q.source === 'builtin' ? 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400' : 'bg-amber-50 text-amber-600 dark:bg-amber-500/15 dark:text-amber-400'"
                >
                  {{ q.source === 'builtin' ? '内置' : '自建' }}
                </span>
                <span v-if="q.type" class="text-[10px] text-slate-400">{{ q.type }}</span>
              </div>
              <p class="line-clamp-2 text-sm text-slate-700 dark:text-slate-200">{{ q.content }}</p>
              <p v-if="q.options.length" class="mt-1 text-xs text-slate-400">
                {{ q.options.map((o) => `${o.option_key}. ${o.content}`).join('　') }}
              </p>
            </div>
            <div v-if="!editMode" class="flex shrink-0 items-center gap-1">
              <button class="btn-icon hover:!text-violet-500 hover:!bg-violet-50 dark:hover:!bg-violet-500/10" title="举一反三" :disabled="loadingSimilar === q.id" @click="generateSimilar(q)">
                <Sparkles :size="14" />
              </button>
              <button v-if="q.source !== 'builtin'" class="btn-icon hover:!text-indigo-500 hover:!bg-indigo-50 dark:hover:!bg-indigo-500/10" title="编辑" @click="router.push(`/questions/add?edit=${q.id}`)">
                <Pencil :size="14" />
              </button>
              <button v-if="q.source !== 'builtin'" class="btn-icon hover:!text-rose-500 hover:!bg-rose-50 dark:hover:!bg-rose-500/10" title="删除" @click="remove(q)">
                <Trash2 :size="14" />
              </button>
            </div>
          </div>

          <!-- 举一反三结果 -->
          <div v-for="(s, i) in Object.entries(similarMap).filter(([id]) => qs.some((q) => q.id === Number(id)))" :key="i" class="border-t border-violet-200 bg-violet-50/50 px-5 py-3 dark:border-violet-500/30 dark:bg-violet-500/10 animate-fade-in">
            <p class="mb-1 flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-violet-600 dark:text-violet-400">
              <Sparkles :size="12" /> 举一反三 · 同类型题
            </p>
            <MarkdownContent :content="s[1].content" />
            <p class="mt-1 text-sm font-medium text-emerald-600 dark:text-emerald-400">答案：{{ s[1].answer }}</p>
            <button class="btn-primary mt-2 !py-1 text-xs" @click="saveSimilar(qs.find((q) => q.id === Number(s[0]))!)">收藏到题库</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
