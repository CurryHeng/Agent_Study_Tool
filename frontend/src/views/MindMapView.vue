<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Network } from 'lucide-vue-next'
import { mindmapApi, workbookApi } from '../api'
import { SYSTEM_WORKBOOK_ID } from '../lib/constants'
import type { MindMapNode, Workbook } from '../types'
import MindMap from '../components/MindMap.vue'

const route = useRoute()
const workbooks = ref<Workbook[]>([])
const selected = ref<number>(SYSTEM_WORKBOOK_ID)
const root = ref<MindMapNode | null>(null)

const builtin: Workbook = {
  id: SYSTEM_WORKBOOK_ID,
  user_id: 0,
  name: '内置题库',
  description: '系统内置参考题库（只读）',
  created_at: '',
  updated_at: '',
}

const options = computed(() => [builtin, ...workbooks.value])

async function load() {
  workbooks.value = await workbookApi.list()
  const fromQuery = route.query.workbook_id
  selected.value = fromQuery != null ? Number(fromQuery) : SYSTEM_WORKBOOK_ID
  await loadMindmap()
}

async function loadMindmap() {
  const data = await mindmapApi.get(selected.value)
  root.value = data.root
}

watch(selected, loadMindmap)
onMounted(load)
</script>

<template>
  <div>
    <h2 class="mb-3 flex items-center gap-2 text-xl font-bold text-slate-800 dark:text-white">
      <Network :size="20" class="text-indigo-500" />
      思维导图
    </h2>
    <select v-model="selected" class="input mb-4 max-w-xs">
      <option v-for="wb in options" :key="wb.id" :value="wb.id">{{ wb.name }}</option>
    </select>

    <div class="card overflow-auto">
      <MindMap v-if="root && root.children.length > 0" :root="root" />
      <p v-else class="text-sm text-slate-400 dark:text-slate-500">
        暂无知识结构。上传资料或使用 AI 助手生成题目后，会自动构建知识树。
      </p>
    </div>
  </div>
</template>
