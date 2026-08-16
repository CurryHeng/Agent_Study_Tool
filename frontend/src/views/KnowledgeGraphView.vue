<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Loader2, Network } from 'lucide-vue-next'
import { knowledgeGraphApi, workbookApi } from '../api'
import { SYSTEM_WORKBOOK_ID } from '../lib/constants'
import type { KnowledgeGraph, Workbook } from '../types'

const workbooks = ref<Workbook[]>([])
const selected = ref<number>(SYSTEM_WORKBOOK_ID)
const graph = ref<KnowledgeGraph | null>(null)
const loading = ref(true)
const error = ref('')

const builtin: Workbook = {
  id: SYSTEM_WORKBOOK_ID,
  user_id: 0,
  name: '内置题库',
  description: '系统内置参考题库（只读）',
  created_at: '',
  updated_at: '',
}
const options = computed(() => [builtin, ...workbooks.value])

const positioned = computed(() => {
  if (!graph.value) return new Map<number, { x: number; y: number }>()
  const nodes = graph.value.nodes
  const byLevel = new Map<number, number[]>()
  for (const n of nodes) {
    const arr = byLevel.get(n.level) ?? []
    arr.push(n.id)
    byLevel.set(n.level, arr)
  }
  const pos = new Map<number, { x: number; y: number }>()
  for (const [level, ids] of byLevel) {
    ids.forEach((id, i) => {
      pos.set(id, { x: 80 + level * 180, y: 60 + i * 90 })
    })
  }
  return pos
})

const W = 900
const H = 600

async function load() {
  loading.value = true
  error.value = ''
  try {
    graph.value = await knowledgeGraphApi.get(selected.value)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载知识图谱失败'
  } finally {
    loading.value = false
  }
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
        <Network :size="20" class="text-indigo-500" />
        知识图谱
      </h2>
      <select v-model="selected" class="input max-w-xs" @change="load">
        <option v-for="wb in options" :key="wb.id" :value="wb.id">{{ wb.name }}</option>
      </select>
    </div>

    <div v-if="loading" class="card flex items-center justify-center gap-2 py-12 text-sm text-slate-400">
      <Loader2 :size="16" class="animate-spin" />
      加载中…
    </div>
    <p v-else-if="error" class="card text-sm text-rose-500">{{ error }}</p>

    <div v-else-if="graph && graph.nodes.length" class="card overflow-auto">
      <svg :width="W" :height="H" :viewBox="`0 0 ${W} ${H}`" class="min-w-[600px]">
        <g v-for="(e, i) in graph.edges" :key="i">
          <line
            :x1="positioned.get(e.source)?.x ?? 0"
            :y1="positioned.get(e.source)?.y ?? 0"
            :x2="positioned.get(e.target)?.x ?? 0"
            :y2="positioned.get(e.target)?.y ?? 0"
            :stroke="e.type === 'parent' ? '#94a3b8' : '#f59e0b'"
            stroke-width="1.5"
          />
        </g>
        <g v-for="n in graph.nodes" :key="n.id">
          <circle
            :cx="positioned.get(n.id)?.x ?? 0"
            :cy="positioned.get(n.id)?.y ?? 0"
            r="22"
            fill="#6366f1"
            opacity="0.85"
          />
          <text
            :x="positioned.get(n.id)?.x ?? 0"
            :y="(positioned.get(n.id)?.y ?? 0) + 4"
            text-anchor="middle"
            fill="white"
            font-size="10"
          >
            {{ n.name.slice(0, 8) }}
          </text>
        </g>
      </svg>
    </div>

    <p v-else class="card py-12 text-center text-sm text-slate-400">
      暂无知识结构，请先导入资料生成知识点。
    </p>
  </div>
</template>
