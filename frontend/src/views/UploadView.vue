<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  BookOpen,
  Database,
  File,
  FileText,
  FileType,
  Folder,
  Image as ImageIcon,
  Loader2,
  RefreshCw,
  Trash2,
  UploadCloud,
  ChevronDown,
  ChevronRight,
} from 'lucide-vue-next'
import { documentApi, workbookApi } from '../api'
import { SYSTEM_WORKBOOK_ID } from '../lib/constants'
import type { Document, DocumentDetail, Workbook } from '../types'

const ALLOWED = ['.pdf', '.docx', '.pptx', '.md', '.txt', '.html', '.htm']
const MAX_SIZE = 10 * 1024 * 1024 // 与后端 config.max_file_size 保持一致

const workbooks = ref<Workbook[]>([])
const builtin: Workbook = {
  id: SYSTEM_WORKBOOK_ID,
  user_id: 0,
  name: '内置题库',
  description: '系统内置题库（只读）',
  created_at: '',
  updated_at: '',
}
const options = computed(() => [builtin, ...workbooks.value])

const selected = ref<number>(SYSTEM_WORKBOOK_ID)
const docs = ref<Document[]>([])
const loading = ref(false)
const uploading = ref(false)
const progress = ref(0)
const dragOver = ref(false)
const deletingId = ref<number | null>(null)
const indexingId = ref<number | null>(null)
const error = ref('')
const expandedId = ref<number | null>(null)
const detailMap = ref<Record<number, DocumentDetail>>({})
const loadingDetail = ref<number | null>(null)

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function typeIcon(type: string) {
  const cls = 'shrink-0'
  if (type === 'pdf') return { icon: FileText, cls: `${cls} text-rose-500` }
  if (type === 'docx' || type === 'pptx') return { icon: FileType, cls: `${cls} text-blue-500` }
  if (type === 'md' || type === 'txt' || type === 'html') return { icon: FileText, cls: `${cls} text-emerald-500` }
  if (type === 'image') return { icon: ImageIcon, cls: `${cls} text-purple-500` }
  return { icon: File, cls: `${cls} text-slate-400` }
}

function statusBadge(status: string) {
  const map: Record<string, { text: string; cls: string }> = {
    success: { text: '已解析', cls: 'bg-emerald-50 text-emerald-600 dark:bg-emerald-500/15 dark:text-emerald-400' },
    processing: { text: '处理中', cls: 'bg-blue-50 text-blue-600 dark:bg-blue-500/15 dark:text-blue-400' },
    failed: { text: '失败', cls: 'bg-rose-50 text-rose-500 dark:bg-rose-500/15 dark:text-rose-400' },
  }
  const s = map[status] || { text: '已上传', cls: 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400' }
  return s
}

// 按 level 分组展示解析出的章节（预览）
const expandedSections = computed(() => detailMap.value[expandedId.value ?? -1]?.sections || [])

async function load() {
  workbooks.value = await workbookApi.list()
  await loadDocs()
}

async function loadDocs() {
  loading.value = true
  try {
    docs.value = await documentApi.list(selected.value)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function handleFile(file: File) {
  const ext = '.' + (file.name.split('.').pop() || '').toLowerCase()
  if (!ALLOWED.includes(ext)) {
    error.value = `不支持的文件类型：${ext || '未知'}`
    return
  }
  if (file.size > MAX_SIZE) {
    error.value = '文件超过 10MB 限制'
    return
  }
  if (selected.value === SYSTEM_WORKBOOK_ID) {
    error.value = '内置题库为只读，请先选择或创建一个自己的练习册再导入'
    return
  }
  error.value = ''
  uploading.value = true
  progress.value = 0
  try {
    await documentApi.upload(file, selected.value, (pct) => (progress.value = pct))
    await loadDocs()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '上传失败'
  } finally {
    uploading.value = false
  }
}

function onDrop(e: DragEvent) {
  e.preventDefault()
  dragOver.value = false
  for (const f of Array.from(e.dataTransfer?.files || [])) handleFile(f)
}

function onSelect(e: Event) {
  const input = e.target as HTMLInputElement
  for (const f of Array.from(input.files || [])) handleFile(f)
  input.value = ''
}

async function remove(doc: Document) {
  if (!confirm(`确定删除文档「${doc.filename}」？`)) return
  deletingId.value = doc.id
  try {
    await documentApi.remove(doc.id)
    if (expandedId.value === doc.id) {
      expandedId.value = null
      delete detailMap.value[doc.id]
    }
    await loadDocs()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '删除失败'
  } finally {
    deletingId.value = null
  }
}

async function reindex(doc: Document) {
  indexingId.value = doc.id
  try {
    await documentApi.index(doc.id)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '索引失败'
  } finally {
    indexingId.value = null
  }
}

async function toggleExpand(doc: Document) {
  if (expandedId.value === doc.id) {
    expandedId.value = null
    return
  }
  expandedId.value = doc.id
  if (detailMap.value[doc.id]) return
  loadingDetail.value = doc.id
  try {
    detailMap.value[doc.id] = await documentApi.get(doc.id)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载解析结果失败'
  } finally {
    loadingDetail.value = null
  }
}

onMounted(load)
</script>

<template>
  <div class="space-y-5 animate-fade-in">
    <h1 class="flex items-center gap-2 text-xl font-bold text-slate-800 dark:text-white">
      <UploadCloud :size="20" class="text-emerald-500" />
      导入资料
    </h1>

    <!-- 选择练习册 -->
    <div class="flex items-center gap-2">
      <Folder :size="16" class="shrink-0 text-slate-400" />
      <select v-model="selected" class="input max-w-xs" @change="loadDocs">
        <option v-for="wb in options" :key="wb.id" :value="wb.id">{{ wb.name }}</option>
      </select>
      <span class="hidden text-xs text-slate-400 sm:inline">导入的资料会归入所选练习册</span>
    </div>

    <!-- 上传区 -->
    <div
      class="cursor-pointer rounded-2xl border-2 border-dashed p-10 text-center transition-all duration-200"
      :class="[
        dragOver
          ? 'border-emerald-400 bg-emerald-50/50 dark:bg-emerald-500/10'
          : 'border-slate-200 bg-white hover:border-emerald-300 hover:bg-slate-50/50 dark:border-slate-700 dark:bg-slate-900',
        { 'pointer-events-none opacity-60': uploading },
      ]"
      @dragover.prevent="dragOver = true"
      @dragleave="dragOver = false"
      @drop="onDrop"
      @click="($refs.fileInput as HTMLInputElement).click()"
    >
      <input ref="fileInput" type="file" :accept="ALLOWED.join(',')" class="hidden" @change="onSelect" />
      <UploadCloud :size="40" class="mx-auto mb-3" :class="dragOver ? 'text-emerald-500' : 'text-slate-300 dark:text-slate-600'" />
      <p class="text-sm font-medium text-slate-600 dark:text-slate-300">点击或拖拽文件到此处上传</p>
      <p class="mt-1.5 text-xs text-slate-400">支持 PDF / Word / PPT / Markdown / TXT / HTML · 最大 10MB</p>
    </div>

    <p v-if="error" class="rounded-xl border border-rose-200 bg-rose-50 px-4 py-2.5 text-sm text-rose-600 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-400">
      {{ error }}
    </p>

    <!-- 上传进度 -->
    <div v-if="uploading" class="card flex items-center gap-3 animate-slide-up">
      <Loader2 :size="18" class="animate-spin text-emerald-500" />
      <div class="min-w-0 flex-1">
        <p class="truncate text-sm text-slate-600 dark:text-slate-300">正在上传并解析…</p>
        <div class="mt-1.5 h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
          <div
            class="progress-bar h-full rounded-full bg-gradient-to-r from-emerald-500 to-teal-500 transition-all duration-300"
            :style="{ width: `${progress}%` }"
          ></div>
        </div>
      </div>
      <span class="text-xs tabular-nums text-slate-400">{{ progress }}%</span>
    </div>

    <!-- 资料库 -->
    <section class="card divide-y divide-slate-100 !p-0 dark:divide-slate-800">
      <div v-if="loading" class="py-10 text-center">
        <Loader2 :size="20" class="mx-auto animate-spin text-slate-300 dark:text-slate-600" />
      </div>

      <div v-else-if="docs.length === 0" class="py-12 text-center text-slate-400">
        <Database :size="36" class="mx-auto mb-3 opacity-40" />
        <p class="text-sm">还没有导入任何资料</p>
        <p class="mt-1 text-xs">上传文档后会自动解析并构建知识点</p>
      </div>

      <div v-for="doc in docs" :key="doc.id">
        <!-- 文档行 -->
        <div class="flex items-center justify-between gap-3 px-5 py-3.5 transition hover:bg-slate-50/60 dark:hover:bg-slate-800/40">
          <div class="flex min-w-0 items-center gap-3">
            <component :is="typeIcon(doc.file_type).icon" :size="18" :class="typeIcon(doc.file_type).cls" />
            <div class="min-w-0">
              <p class="truncate text-sm font-medium text-slate-700 dark:text-slate-200">{{ doc.filename }}</p>
              <p class="text-xs text-slate-400">
                {{ doc.file_type?.toUpperCase() }} · {{ formatSize(doc.file_size) }} · {{ doc.created_at?.slice(0, 10) }}
                <span class="ml-1.5" :class="statusBadge(doc.status).cls">{{ statusBadge(doc.status).text }}</span>
              </p>
            </div>
          </div>
          <div class="flex shrink-0 items-center gap-1">
            <button
              v-if="doc.status === 'success'"
              class="btn-icon"
              :title="expandedId === doc.id ? '收起' : '查看解析结果'"
              @click="toggleExpand(doc)"
            >
              <Loader2 v-if="loadingDetail === doc.id" :size="15" class="animate-spin" />
              <ChevronDown v-else-if="expandedId === doc.id" :size="15" />
              <ChevronRight v-else :size="15" />
            </button>
            <button class="btn-icon" title="重新构建向量索引" :disabled="indexingId === doc.id" @click="reindex(doc)">
              <RefreshCw v-if="indexingId === doc.id" :size="15" class="animate-spin" />
              <BookOpen v-else :size="15" />
            </button>
            <button class="btn-icon hover:!text-rose-500 hover:!bg-rose-50 dark:hover:!bg-rose-500/10" title="删除" :disabled="deletingId === doc.id" @click="remove(doc)">
              <Loader2 v-if="deletingId === doc.id" :size="15" class="animate-spin" />
              <Trash2 v-else :size="15" />
            </button>
          </div>
        </div>

        <!-- 展开的解析结果预览 -->
        <div v-if="expandedId === doc.id" class="border-t border-slate-100 bg-slate-50/40 px-5 py-4 dark:border-slate-800 dark:bg-slate-800/30 animate-slide-up">
          <div v-if="loadingDetail === doc.id" class="py-4 text-center text-sm text-slate-400">加载解析结果…</div>
          <div v-else-if="expandedSections.length === 0" class="py-2 text-sm text-slate-400">该文档未解析出章节结构。</div>
          <div v-else class="space-y-1">
            <div
              v-for="(s, i) in expandedSections"
              :key="i"
              class="flex items-center gap-2 text-sm"
              :style="{ paddingLeft: `${Math.max(0, (s.level || 1) - 1) * 1.25}rem` }"
            >
              <span
                class="shrink-0 rounded px-1 py-0.5 text-[10px] font-medium"
                :class="s.level <= 1 ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-400' : 'bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400'"
              >
                章节 {{ s.level }}
              </span>
              <span class="truncate text-slate-700 dark:text-slate-200">{{ s.title }}</span>
              <span v-if="s.paragraphs?.length" class="ml-auto shrink-0 text-xs text-slate-400">{{ s.paragraphs.length }} 段</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
