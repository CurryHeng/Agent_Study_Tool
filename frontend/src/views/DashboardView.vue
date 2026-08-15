<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  BarChart3,
  BookX,
  ChevronRight,
  Library,
  Loader2,
  Network,
  Play,
  Sparkles,
  UploadCloud,
} from 'lucide-vue-next'
import { documentApi, reviewApi, workbookApi } from '../api'
import { SYSTEM_WORKBOOK_ID } from '../lib/constants'
import type { Document, Workbook } from '../types'

const router = useRouter()
const workbooks = ref<Workbook[]>([])
const dueCount = ref(0)

// ── 导入 ──
const selectedWb = ref<number | null>(null)
const docs = ref<Document[]>([])
const uploading = ref(false)
const uploadError = ref('')
const uploadOk = ref('')

const ALLOWED = ['.pdf', '.docx', '.pptx', '.md', '.txt', '.html', '.htm']
const MAX_SIZE = 10 * 1024 * 1024

const userWorkbooks = computed(() => workbooks.value.filter((w) => w.id !== SYSTEM_WORKBOOK_ID))

const cards = [
  { to: '/review', label: '刷题复习', desc: 'FSRS 智能安排', icon: Play, color: 'from-emerald-500 to-teal-600' },
  { to: '/questions', label: '题库', desc: '浏览 / AI 出题', icon: Library, color: 'from-indigo-500 to-violet-600' },
  { to: '/mindmap', label: '可视化', desc: '知识思维导图', icon: Network, color: 'from-sky-500 to-blue-600' },
  { to: '/wrong', label: '错题本', desc: '错因与回顾', icon: BookX, color: 'from-rose-500 to-pink-600' },
  { to: '/stats', label: '统计', desc: '掌握度热力图', icon: BarChart3, color: 'from-amber-500 to-orange-600' },
  { to: '/assistant', label: '智能助手', desc: '对话完成任务', icon: Sparkles, color: 'from-violet-500 to-purple-600' },
]

async function load() {
  workbooks.value = await workbookApi.list()
  if (!selectedWb.value && userWorkbooks.value.length) {
    selectedWb.value = userWorkbooks.value[0].id
  }
  if (selectedWb.value) await loadDocs()
  dueCount.value = (await reviewApi.due(50)).length
}

async function loadDocs() {
  if (!selectedWb.value) return
  docs.value = await documentApi.list(selectedWb.value)
}

async function onPickFile(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  ;(e.target as HTMLInputElement).value = ''
  if (!file) return
  const ext = '.' + (file.name.split('.').pop() || '').toLowerCase()
  uploadError.value = ''
  uploadOk.value = ''
  if (!ALLOWED.includes(ext)) {
    uploadError.value = `不支持的文件类型：${ext}`
    return
  }
  if (file.size > MAX_SIZE) {
    uploadError.value = '文件超过 10MB 限制'
    return
  }
  if (!selectedWb.value) {
    uploadError.value = '请先创建练习册'
    return
  }
  uploading.value = true
  try {
    await documentApi.upload(file, selectedWb.value)
    uploadOk.value = `「${file.name}」导入成功，知识树已自动生成`
    await loadDocs()
  } catch (err) {
    uploadError.value = err instanceof Error ? err.message : '上传失败'
  } finally {
    uploading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="space-y-6">
    <!-- 欢迎条 -->
    <section class="hero-grad relative overflow-hidden rounded-3xl p-7 text-white shadow-xl shadow-emerald-600/20">
      <p class="text-sm font-medium text-emerald-100">EStudy · 你的 AI 学习伙伴</p>
      <h1 class="mt-1.5 text-2xl font-bold tracking-tight">
        {{ dueCount > 0 ? `今天有 ${dueCount} 道题待复习` : '今日复习已完成' }}
      </h1>
      <button
        class="mt-4 inline-flex items-center gap-2 rounded-xl bg-white px-4 py-2 text-sm font-semibold text-teal-700 shadow-md transition hover:bg-emerald-50 active:scale-[0.98]"
        @click="router.push('/review')"
      >
        <Play :size="15" class="fill-current" />
        开始刷题
      </button>
    </section>

    <!-- 导入资料 -->
    <section class="card">
      <h3 class="mb-3 flex items-center gap-2 font-semibold text-slate-800 dark:text-white">
        <UploadCloud :size="17" class="text-indigo-500" />
        导入学习资料
      </h3>
      <div class="flex flex-wrap items-center gap-2">
        <select v-model="selectedWb" class="input !w-auto !py-1.5 text-sm" @change="loadDocs">
          <option :value="null" disabled>选择练习册</option>
          <option v-for="wb in userWorkbooks" :key="wb.id" :value="wb.id">{{ wb.name }}</option>
        </select>
        <label
          class="btn-primary inline-flex cursor-pointer items-center gap-2 !py-1.5 text-sm"
          :class="uploading ? 'pointer-events-none opacity-60' : ''"
        >
          <Loader2 v-if="uploading" :size="14" class="animate-spin" />
          <UploadCloud v-else :size="14" />
          {{ uploading ? '导入中…' : '选择文件' }}
          <input type="file" class="hidden" :accept="ALLOWED.join(',')" @change="onPickFile" />
        </label>
        <span class="text-xs text-slate-400">支持 PDF / Word / PPT / Markdown，≤10MB，导入后自动生成知识树</span>
      </div>
      <p v-if="uploadError" class="mt-2 text-xs text-rose-500">{{ uploadError }}</p>
      <p v-if="uploadOk" class="mt-2 text-xs text-emerald-600 dark:text-emerald-400">{{ uploadOk }}</p>
      <div v-if="docs.length" class="mt-3 flex flex-wrap gap-2">
        <span
          v-for="d in docs.slice(0, 6)"
          :key="d.id"
          class="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-500 dark:bg-slate-800 dark:text-slate-400"
        >
          {{ d.filename }}
        </span>
        <span v-if="docs.length > 6" class="px-1 py-1 text-xs text-slate-400">等 {{ docs.length }} 份</span>
      </div>
    </section>

    <!-- 功能卡片（自由选择） -->
    <section class="grid grid-cols-2 gap-3 sm:grid-cols-3">
      <button
        v-for="c in cards"
        :key="c.to"
        class="card card-hover flex flex-col items-start gap-2 text-left"
        @click="router.push(c.to)"
      >
        <span
          class="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br text-white"
          :class="c.color"
        >
          <component :is="c.icon" :size="18" />
        </span>
        <div class="flex w-full items-center justify-between">
          <p class="font-semibold text-slate-800 dark:text-white">{{ c.label }}</p>
          <ChevronRight :size="15" class="text-slate-300" />
        </div>
        <p class="text-xs text-slate-400">{{ c.desc }}</p>
      </button>
    </section>

    <!-- 我的练习册 -->
    <section v-if="userWorkbooks.length">
      <h3 class="mb-3 font-semibold text-slate-800 dark:text-white">我的练习册</h3>
      <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div v-for="wb in userWorkbooks" :key="wb.id" class="card card-hover">
          <p class="font-medium text-slate-700 dark:text-slate-200">{{ wb.name }}</p>
          <div class="mt-3 flex gap-2">
            <button class="btn-secondary flex-1 !py-1.5 text-xs" @click="router.push(`/questions?workbook_id=${wb.id}`)">
              题库
            </button>
            <button class="btn-secondary flex-1 !py-1.5 text-xs" @click="router.push(`/mindmap?workbook_id=${wb.id}`)">
              可视化
            </button>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
