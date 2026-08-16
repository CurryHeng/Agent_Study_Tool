<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { History, Loader2 } from 'lucide-vue-next'
import { historyApi } from '../api'
import type { HistoryEvent } from '../types'

const events = ref<HistoryEvent[]>([])
const loading = ref(true)
const error = ref('')

const TYPE_META: Record<string, { label: string; cls: string }> = {
  upload: { label: '上传', cls: 'bg-sky-100 text-sky-600 dark:bg-sky-500/15 dark:text-sky-400' },
  generate: { label: '出题', cls: 'bg-violet-100 text-violet-600 dark:bg-violet-500/15 dark:text-violet-400' },
  answer: { label: '答题', cls: 'bg-emerald-100 text-emerald-600 dark:bg-emerald-500/15 dark:text-emerald-400' },
  wrong: { label: '错题', cls: 'bg-rose-100 text-rose-600 dark:bg-rose-500/15 dark:text-rose-400' },
  review: { label: '复习', cls: 'bg-amber-100 text-amber-600 dark:bg-amber-500/15 dark:text-amber-400' },
}

onMounted(async () => {
  try {
    events.value = await historyApi.list()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载时间线失败'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="space-y-4 animate-fade-in">
    <h2 class="flex items-center gap-2 text-xl font-bold text-slate-800 dark:text-white">
      <History :size="20" class="text-indigo-500" />
      学习活动时间线
    </h2>

    <div v-if="loading" class="card flex items-center justify-center gap-2 py-12 text-sm text-slate-400">
      <Loader2 :size="16" class="animate-spin" />
      加载中…
    </div>
    <p v-else-if="error" class="card text-sm text-rose-500">{{ error }}</p>

    <div v-else-if="events.length === 0" class="card py-12 text-center text-sm text-slate-400">
      还没有学习活动，去上传资料、出题或刷题吧。
    </div>

    <div v-else class="space-y-2">
      <div
        v-for="e in events"
        :key="e.id"
        class="card card-hover flex items-start gap-3 !p-4"
      >
        <span class="badge mt-0.5 shrink-0" :class="TYPE_META[e.type]?.cls || 'bg-slate-100 text-slate-500'">
          {{ TYPE_META[e.type]?.label || e.type }}
        </span>
        <div class="min-w-0 flex-1">
          <p class="text-sm font-semibold text-slate-800 dark:text-white">{{ e.title }}</p>
          <p v-if="e.detail" class="mt-0.5 truncate text-xs text-slate-500 dark:text-slate-400">{{ e.detail }}</p>
        </div>
        <span class="shrink-0 text-[10px] tabular-nums text-slate-400">{{ e.created_at?.slice(0, 16).replace('T', ' ') }}</span>
      </div>
    </div>
  </div>
</template>
