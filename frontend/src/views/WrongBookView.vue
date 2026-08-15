<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { BookMarked, Pencil } from 'lucide-vue-next'
import { wrongRecordApi } from '../api'
import type { WrongRecord } from '../types'
import MarkdownContent from '../components/MarkdownContent.vue'

const TYPE_LABEL: Record<string, string> = {
  single_choice: '单选题',
  multiple_choice: '多选题',
  true_false: '判断题',
  fill_blank: '填空题',
  short_answer: '简答题',
}

const records = ref<WrongRecord[]>([])
const route = useRoute()
const router = useRouter()
const knowledgeFilterId = computed(() => {
  const raw = route.query.knowledge_id
  return raw != null ? Number(raw) : null
})
const typeFilter = ref('all')
const editingId = ref<number | null>(null)
const editReason = ref('')

const filtered = computed(() => {
  if (typeFilter.value === 'all') return records.value
  return records.value.filter((r) => r.question_type === typeFilter.value)
})

async function load() {
  records.value = await wrongRecordApi.list(knowledgeFilterId.value)
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
watch(() => route.query.knowledge_id, load)
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
        <div v-else class="mt-3 flex items-start justify-between gap-2">
          <p class="text-xs text-slate-500 dark:text-slate-400">
            <span class="font-medium text-slate-600 dark:text-slate-300">错因：</span>{{ r.wrong_reason || '（未记录）' }}
          </p>
          <button class="flex shrink-0 items-center gap-1 text-xs text-indigo-500 transition hover:text-indigo-700 dark:text-indigo-400" @click="startEdit(r)">
            <Pencil :size="12" />
            {{ r.wrong_reason ? '编辑' : '标注错因' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
