<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { FileText, Loader2, RefreshCw, Trash2, UploadCloud } from 'lucide-vue-next'
import { documentApi, workbookApi } from '../api'
import { SYSTEM_WORKBOOK_ID } from '../lib/constants'
import type { Document, Workbook } from '../types'

const router = useRouter()
const workbooks = ref<Workbook[]>([])
const selected = ref<number>(SYSTEM_WORKBOOK_ID)
const documents = ref<Document[]>([])
const loading = ref(false)
const uploading = ref(false)
const error = ref('')
const ok = ref('')
const autoGenerate = ref(false)
const genType = ref('single_choice')
const genCount = ref(5)
const genDifficulty = ref(1)
const genScope = ref('')
const lastGenerated = ref(0)

const TYPE_OPTIONS = [
  { value: 'single_choice', label: '单选题' },
  { value: 'multiple_choice', label: '多选题' },
  { value: 'true_false', label: '判断题' },
  { value: 'fill_blank', label: '填空题' },
  { value: 'short_answer', label: '简答题' },
]

const builtin: Workbook = {
  id: SYSTEM_WORKBOOK_ID,
  user_id: 0,
  name: '内置题库',
  description: '系统内置参考题库（只读）',
  created_at: '',
  updated_at: '',
}
const options = computed(() => [builtin, ...workbooks.value])

const ALLOWED = ['.pdf', '.docx', '.pptx', '.md', '.txt', '.html', '.htm', '.png', '.jpg', '.jpeg']
const MAX_SIZE = 10 * 1024 * 1024

const STATUS_LABEL: Record<string, string> = {
  pending: '等待中',
  processing: '处理中',
  success: '成功',
  failed: '失败',
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    documents.value = await documentApi.list(selected.value)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载文件库失败'
  } finally {
    loading.value = false
  }
}

async function onPickFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  const ext = '.' + (file.name.split('.').pop() || '').toLowerCase()
  if (!ALLOWED.includes(ext)) {
    error.value = `不支持的文件格式：${ext}`
    return
  }
  if (file.size > MAX_SIZE) {
    error.value = '文件不能超过 10MB'
    return
  }
  uploading.value = true
  error.value = ''
  ok.value = ''
  try {
    const resp = await documentApi.upload(file, selected.value, {
      autoGenerate: autoGenerate.value,
      questionType: genType.value,
      count: genCount.value,
      difficulty: genDifficulty.value,
      scope: genScope.value || undefined,
    })
    lastGenerated.value = resp.generated_questions?.length ?? 0
    ok.value = lastGenerated.value > 0
      ? `上传成功，已生成 ${lastGenerated.value} 道题目预览`
      : '上传成功，正在解析并生成知识结构…'
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '上传失败'
  } finally {
    uploading.value = false
    input.value = ''
  }
}

async function remove(doc: Document) {
  if (!confirm(`确定删除「${doc.filename}」？`)) return
  try {
    await documentApi.remove(doc.id)
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '删除失败'
  }
}

function viewInVisualization() {
  router.push({ path: '/visualization', query: { tab: 'mindmap', workbook_id: String(selected.value) } })
}

onMounted(async () => {
  try {
    workbooks.value = await workbookApi.list()
  } catch {
    workbooks.value = []
  }
  await load()
})
</script>

<template>
  <div class="space-y-4 animate-fade-in">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h2 class="flex items-center gap-2 text-xl font-bold text-slate-800 dark:text-white">
        <FileText :size="20" class="text-indigo-500" />
        文件库
      </h2>
      <div class="flex items-center gap-2">
        <select v-model="selected" class="input max-w-xs" @change="load">
          <option v-for="wb in options" :key="wb.id" :value="wb.id">{{ wb.name }}</option>
        </select>
        <button class="btn-secondary !py-1.5 text-xs" @click="viewInVisualization">
          <RefreshCw :size="13" /> 查看可视化
        </button>
      </div>
    </div>

    <div v-if="error" class="rounded-xl border border-rose-200 bg-rose-50 px-4 py-2.5 text-sm text-rose-600 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-400">
      {{ error }}
    </div>
    <div v-if="ok" class="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-400">
      {{ ok }}
    </div>
    <p v-if="lastGenerated > 0" class="text-xs text-indigo-500 dark:text-indigo-400">
      已生成 {{ lastGenerated }} 道题目预览（未入库），可到题库页确认/重新生成。
    </p>

    <!-- 上传区 -->
    <div class="card flex flex-col items-center justify-center gap-2 border-dashed py-10 text-center">
      <UploadCloud :size="28" class="text-indigo-400" />
      <p class="text-sm text-slate-500 dark:text-slate-400">支持 PDF / Word / PPT / Markdown / TXT / HTML / 图片，≤10MB</p>

      <div class="mt-3 grid w-full max-w-2xl grid-cols-2 gap-2 text-left sm:grid-cols-4">
        <label class="col-span-2 flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
          <input v-model="autoGenerate" type="checkbox" class="accent-indigo-500" />
          导入后自动生成题目
        </label>
        <select v-model="genType" class="input" :disabled="!autoGenerate">
          <option v-for="t in TYPE_OPTIONS" :key="t.value" :value="t.value">{{ t.label }}</option>
        </select>
        <input v-model.number="genCount" type="number" min="1" max="20" class="input" placeholder="题数" :disabled="!autoGenerate" />
        <input v-model.number="genDifficulty" type="number" min="1" max="5" class="input" placeholder="难度" :disabled="!autoGenerate" />
        <input v-model="genScope" class="input" placeholder="范围/章节（可选）" :disabled="!autoGenerate" />
      </div>

      <label class="btn-primary mt-2 cursor-pointer">
        <Loader2 v-if="uploading" :size="15" class="animate-spin" />
        <UploadCloud v-else :size="15" />
        {{ uploading ? '上传中…' : '上传文档' }}
        <input type="file" class="hidden" :accept="ALLOWED.join(',')" @change="onPickFile" />
      </label>
    </div>

    <!-- 文档列表 -->
    <div v-if="loading" class="card flex items-center justify-center gap-2 py-10 text-sm text-slate-400">
      <Loader2 :size="16" class="animate-spin" /> 加载中…
    </div>

    <div v-else-if="documents.length === 0" class="card py-12 text-center text-sm text-slate-400">
      还没有导入文档，上传后会自动生成提纲/知识树，并可在可视化中查看。
    </div>

    <div v-else class="space-y-2">
      <div v-for="doc in documents" :key="doc.id" class="card card-hover flex items-center gap-3 !p-4">
        <div class="min-w-0 flex-1">
          <p class="truncate text-sm font-semibold text-slate-800 dark:text-white">{{ doc.filename }}</p>
          <p class="mt-0.5 text-xs text-slate-400">
            {{ doc.file_type }} · {{ (doc.file_size / 1024).toFixed(1) }} KB · {{ doc.created_at?.slice(0, 10) }}
          </p>
        </div>
        <span
          class="badge shrink-0"
          :class="
            doc.status === 'success'
              ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-400'
              : doc.status === 'failed'
                ? 'bg-rose-100 text-rose-600 dark:bg-rose-500/15 dark:text-rose-400'
                : 'bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-400'
          "
        >
          {{ STATUS_LABEL[doc.status] || doc.status }}
        </span>
        <button class="btn-icon" title="删除" @click="remove(doc)">
          <Trash2 :size="15" />
        </button>
      </div>
    </div>
  </div>
</template>
