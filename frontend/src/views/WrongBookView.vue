<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { BookMarked, BrainCircuit, Loader2, Pencil, Play } from 'lucide-vue-next'
import { wrongRecordApi } from '../api'
import type { WrongRecord } from '../types'
import MarkdownContent from '../components/MarkdownContent.vue'
import Pagination from '../components/Pagination.vue'

const TYPE_LABEL: Record<string, string> = {
  single_choice: '单选题',
  multiple_choice: '多选题',
  true_false: '判断题',
  fill_blank: '填空题',
  short_answer: '简答题',
}

const records = ref<WrongRecord[]>([])
const totalRecords = ref(0)
const route = useRoute()
const router = useRouter()
const knowledgeFilterId = computed(() => {
  const raw = route.query.knowledge_id
  return raw != null ? Number(raw) : null
})
const typeFilter = ref('all')
const page = ref(1)
const pageSize = ref(10)
const editingId = ref<number | null>(null)
const editReason = ref('')
const analyzingId = ref<number | null>(null)

const filtered = computed(() => records.value)
const totalPages = computed(() => Math.max(1, Math.ceil(totalRecords.value / pageSize.value)))

async function load() {
  const data = await wrongRecordApi.listPage({
    knowledgeId: knowledgeFilterId.value,
    questionType: typeFilter.value === 'all' ? null : typeFilter.value,
    page: page.value,
    pageSize: pageSize.value,
  })
  records.value = data.items
  totalRecords.value = data.total
}

function nextPage() {
  if (page.value >= totalPages.value) return
  page.value++
  load()
}

async function analyze(r: WrongRecord) {
  if (analyzingId.value != null) return
  analyzingId.value = r.id
  try {
    const result = await wrongRecordApi.analyze(r.id)
    r.reason_type = result.reason_type
    r.explanation = result.explanation
    r.suggestion = result.suggestion
  } catch (e) {
    alert(e instanceof Error ? e.message : '分析失败，请确认已配置 AI API')
  } finally {
    analyzingId.value = null
  }
}

function prevPage() {
  if (page.value <= 1) return
  page.value--
  load()
}

function startEdit(r: WrongRecord) {
  editingId.value = r.id
  editReason.value = r.wrong_reason || ''
}

function cancelEdit() {
  editingId.value = null
  editReason.value = ''
}

async function saveEdit(r: WrongRecord) {
  await wrongRecordApi.update(r.id, { wrong_reason: editReason.value })
  await load()
  cancelEdit()
}

onMounted(load)
watch(() => route.query.knowledge_id, () => { page.value = 1; load() })
watch(typeFilter, () => { page.value = 1; load() })
</script>

<template>
  <div>
    <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
      <div class="flex flex-wrap items-center gap-2">
        <h2 class="flex items-center gap-2 text-xl font-bold text-slate-800 dark:text-white">
          <BookMarked :size="20" class="text-rose-500" />
          错题本
        </h2>
        <span v-if="knowledgeFilterId != null" class="badge bg-indigo-50 text-indigo-600 dark:bg-indigo-500/15 dark:text-indigo-300">
          知识点：{{ records[0]?.knowledge_name ?? `#${knowledgeFilterId}` }}
          <button
            class="ml-1 rounded-full px-1 text-indigo-400 transition hover:bg-indigo-100 hover:text-indigo-700 dark:hover:bg-indigo-500/20"
            title="清除筛选"
            @click="router.replace({ path: '/wrong' })"
          >
            ×
          </button>
        </span>
      </div>
      <select v-model="typeFilter" class="input !w-32">
        <option value="all">全部题型</option>
        <option v-for="(label, key) in TYPE_LABEL" :key="key" :value="key">{{ label }}</option>
      </select>
    </div>

    <div
      v-if="filtered.length === 0"
      class="card py-12 text-center text-sm text-slate-400 dark:text-slate-500"
    >
      暂无错题记录，去刷题吧。
    </div>

    <div class="space-y-3">
      <div v-for="r in filtered" :key="r.id" class="card card-hover">
        <div class="mb-2 flex items-center gap-2">
          <span class="badge bg-rose-50 text-rose-500 dark:bg-rose-500/15 dark:text-rose-400">{{ TYPE_LABEL[r.question_type] || r.question_type }}</span>
          <span v-if="r.knowledge_name" class="badge bg-indigo-50 text-indigo-600 dark:bg-indigo-500/15 dark:text-indigo-300">{{ r.knowledge_name }}</span>
          <span class="ml-auto text-[10px] text-slate-400">{{ r.created_at?.slice(0, 10) }}</span>
        </div>

        <MarkdownContent :content="r.question_content" />
        <div class="mt-3 space-y-1 border-t border-slate-100 pt-3 text-sm dark:border-slate-800">
          <p class="text-rose-500 dark:text-rose-400">
            <span class="font-medium">你的答案：</span>{{ r.wrong_answer || '（未填写）' }}
          </p>
          <p class="text-emerald-600 dark:text-emerald-400">
            <span class="font-medium">正确答案：</span>{{ r.correct_answer }}
          </p>
        </div>

        <!-- 错因展示/编辑 -->
        <div v-if="editingId === r.id" class="mt-3">
          <textarea v-model="editReason" rows="2" class="input" placeholder="记录错因，方便日后复习"></textarea>
          <div class="mt-2 flex gap-2">
            <button class="btn-primary !py-1 text-xs" @click="saveEdit(r)">保存</button>
            <button class="btn-ghost !py-1 text-xs" @click="cancelEdit">取消</button>
          </div>
        </div>
        <div v-else class="mt-3 space-y-2">
          <div class="flex items-start justify-between gap-2">
            <p class="text-xs text-slate-500 dark:text-slate-400">
              <span class="font-medium text-slate-600 dark:text-slate-300">错因：</span>{{ r.wrong_reason || '（未记录）' }}
            </p>
            <div class="flex shrink-0 items-center gap-2">
              <button
                class="flex items-center gap-1 text-xs text-violet-500 transition hover:text-violet-700 dark:text-violet-400"
                :disabled="analyzingId === r.id"
                @click="analyze(r)"
              >
                <Loader2 v-if="analyzingId === r.id" :size="12" class="animate-spin" />
                <BrainCircuit v-else :size="12" />
                AI 错因分析
              </button>
              <button
                class="flex items-center gap-1 text-xs text-emerald-600 transition hover:text-emerald-700 dark:text-emerald-400"
                @click="router.push(`/review?question_id=${r.question_id}`)"
              >
                <Play :size="12" class="fill-current" />
                重做此题
              </button>
              <button class="flex items-center gap-1 text-xs text-indigo-500 transition hover:text-indigo-700 dark:text-indigo-400" @click="startEdit(r)">
                <Pencil :size="12" />
                {{ r.wrong_reason ? '编辑' : '标注错因' }}
              </button>
            </div>
          </div>

          <!-- AI 分析结果 -->
          <div v-if="r.reason_type" class="rounded-xl border border-violet-200 bg-violet-50/60 p-3 dark:border-violet-500/30 dark:bg-violet-500/10">
            <span class="badge bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-300">{{ r.reason_type }}</span>
            <p v-if="r.explanation" class="mt-2 text-xs text-slate-600 dark:text-slate-300">{{ r.explanation }}</p>
            <p v-if="r.suggestion" class="mt-1 text-xs text-emerald-700 dark:text-emerald-400">建议：{{ r.suggestion }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <Pagination
      :page="page"
      :page-size="pageSize"
      :has-more="page < totalPages"
      @prev="prevPage"
      @next="nextPage"
    />
  </div>
</template>
