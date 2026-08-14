<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  Award,
  BarChart3,
  CalendarDays,
  Check,
  Clock,
  Layers,
  Loader2,
  Sparkles,
  Star,
  Target,
  TrendingUp,
} from 'lucide-vue-next'
import { statsApi } from '../api'
import type { Stats } from '../types'

const stats = ref<Stats | null>(null)
const loading = ref(true)
const error = ref('')

const MASTERY = [
  { key: 'again', label: '忘记', cls: 'bg-rose-400' },
  { key: 'hard', label: '困难', cls: 'bg-orange-400' },
  { key: 'good', label: '正确', cls: 'bg-emerald-400' },
  { key: 'easy', label: '简单', cls: 'bg-blue-400' },
]
const RATING_LABEL: Record<string, { text: string; cls: string }> = {
  again: { text: '忘记', cls: 'bg-rose-100 text-rose-600 dark:bg-rose-500/15 dark:text-rose-400' },
  hard: { text: '困难', cls: 'bg-orange-100 text-orange-600 dark:bg-orange-500/15 dark:text-orange-400' },
  good: { text: '正确', cls: 'bg-emerald-100 text-emerald-600 dark:bg-emerald-500/15 dark:text-emerald-400' },
  easy: { text: '简单', cls: 'bg-blue-100 text-blue-600 dark:bg-blue-500/15 dark:text-blue-400' },
}
const MODE_LABEL: Record<string, string> = { relaxed: '宽松', normal: '普通', strict: '严格' }

const masteryTotal = computed(() =>
  stats.value ? Object.values(stats.value.mastery).reduce((a, b) => a + b, 0) : 0,
)
const masteredRate = computed(() => {
  if (!stats.value || masteryTotal.value === 0) return 0
  return Math.round(((stats.value.mastery.good + stats.value.mastery.easy) / masteryTotal.value) * 100)
})
const maxBucket = computed(() =>
  Math.max(...(stats.value?.accuracy_buckets.map((b) => b.count) || []), 1),
)
const reasonTotal = computed(() => (stats.value?.wrong_reasons || []).reduce((a, b) => a + b.count, 0))

const REASON_COLORS: Record<string, string> = {
  计算错误: 'bg-rose-400',
  概念不清: 'bg-orange-400',
  公式记错: 'bg-amber-400',
  看错题: 'bg-blue-400',
  其他: 'bg-slate-400',
}

const statItems = computed(() =>
  stats.value
    ? [
        { icon: CalendarDays, label: '待复习', value: String(stats.value.cards_due), color: 'text-blue-500 bg-blue-50 dark:bg-blue-500/15' },
        { icon: Layers, label: '复习卡总数', value: String(stats.value.cards_total), color: 'text-green-500 bg-green-50 dark:bg-green-500/15' },
        { icon: Target, label: '掌握率', value: `${masteredRate.value}%`, color: 'text-purple-500 bg-purple-50 dark:bg-purple-500/15' },
        { icon: Award, label: '题库规模', value: `${stats.value.question_total} 题`, color: 'text-orange-500 bg-orange-50 dark:bg-orange-500/15' },
        { icon: Star, label: '收藏', value: String(stats.value.favorites), color: 'text-amber-500 bg-amber-50 dark:bg-amber-500/15' },
        { icon: Check, label: '今日已复习', value: String(stats.value.reviewed_today), color: 'text-cyan-500 bg-cyan-50 dark:bg-cyan-500/15' },
      ]
    : [],
)

function heatmapCls(rate: number) {
  if (rate > 0.5)
    return 'bg-rose-100 text-rose-700 border-rose-300 dark:bg-rose-500/20 dark:text-rose-300 dark:border-rose-500/40'
  if (rate >= 0.3)
    return 'bg-orange-100 text-orange-700 border-orange-200 dark:bg-orange-500/20 dark:text-orange-300 dark:border-orange-500/40'
  return 'bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-500/20 dark:text-emerald-300 dark:border-emerald-500/40'
}

onMounted(async () => {
  try {
    stats.value = await statsApi.get()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载统计失败'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="space-y-5 animate-fade-in">
    <h1 class="flex items-center gap-2 text-xl font-bold text-slate-800 dark:text-white">
      <BarChart3 :size="20" class="text-emerald-500" />
      学习统计
    </h1>

    <div v-if="loading" class="card py-12 text-center">
      <Loader2 :size="20" class="mx-auto animate-spin text-slate-300 dark:text-slate-600" />
    </div>

    <p v-else-if="error" class="card text-sm text-rose-500">{{ error }}</p>

    <template v-else-if="stats">
      <!-- 大数字 -->
      <div class="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <div v-for="item in statItems" :key="item.label" class="card !p-4">
          <div :class="`mb-2 flex h-9 w-9 items-center justify-center rounded-lg ${item.color}`">
            <component :is="item.icon" :size="18" />
          </div>
          <p class="text-xl font-bold text-slate-800 dark:text-white">{{ item.value }}</p>
          <p class="mt-0.5 text-xs text-slate-400">{{ item.label }}</p>
        </div>
      </div>

      <!-- 掌握分布 -->
      <section v-if="masteryTotal > 0" class="card">
        <h3 class="mb-4 text-sm font-semibold text-slate-800 dark:text-white">掌握分布</h3>
        <div class="flex h-3 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
          <div
            v-for="m in MASTERY"
            :key="m.key"
            :class="m.cls"
            class="h-full transition-all"
            :style="{ width: `${(stats.mastery[m.key] / masteryTotal) * 100}%` }"
          ></div>
        </div>
        <div class="mt-3 flex justify-between text-xs text-slate-500 dark:text-slate-400">
          <span v-for="m in MASTERY" :key="m.key">{{ m.label }} {{ stats.mastery[m.key] }}</span>
        </div>
      </section>

      <!-- 单题正确率分布 -->
      <section v-if="stats.cards_total > 0" class="card">
        <h3 class="mb-4 text-sm font-semibold text-slate-800 dark:text-white">单题正确率分布</h3>
        <div class="flex h-40 items-end gap-3">
          <div
            v-for="b in stats.accuracy_buckets"
            :key="b.label"
            class="flex h-full flex-1 flex-col items-center justify-end gap-1.5"
          >
            <span class="text-xs font-medium text-slate-600 dark:text-slate-300">{{ b.count }}</span>
            <div
              class="w-full rounded-t-lg bg-indigo-500 transition-all duration-500 dark:bg-indigo-400"
              :style="{ height: `${(b.count / maxBucket) * 100}%` }"
            ></div>
            <span class="whitespace-nowrap text-[10px] text-slate-400">{{ b.label }}</span>
          </div>
        </div>
      </section>

      <!-- 本周学习 -->
      <section class="card">
        <h3 class="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-800 dark:text-white">
          <Clock :size="15" class="text-indigo-500" />
          本周学习
        </h3>
        <div class="flex gap-3">
          <div class="flex-1 rounded-xl bg-indigo-50 p-3 text-center dark:bg-indigo-500/10">
            <p class="text-2xl font-bold text-indigo-600 dark:text-indigo-400">{{ stats.week_minutes }}</p>
            <p class="mt-0.5 text-[10px] text-indigo-400">累计分钟</p>
          </div>
          <div class="flex-1 rounded-xl bg-emerald-50 p-3 text-center dark:bg-emerald-500/10">
            <p class="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{{ stats.week_days }}</p>
            <p class="mt-0.5 text-[10px] text-emerald-400">学习天数</p>
          </div>
        </div>
      </section>

      <!-- 知识点掌握热力图 -->
      <section v-if="stats.knowledge_heatmap.length > 0" class="card">
        <h3 class="mb-4 flex items-center gap-1.5 text-sm font-semibold text-slate-800 dark:text-white">
          <Sparkles :size="15" class="text-violet-500" />
          知识点掌握热力图
          <span class="text-xs font-normal text-slate-400">（错误率越高颜色越深）</span>
        </h3>
        <div class="flex flex-wrap gap-2">
          <div
            v-for="k in stats.knowledge_heatmap"
            :key="k.name"
            class="flex cursor-default items-center gap-2 rounded-lg border px-3 py-2 text-xs font-medium transition-transform hover:scale-105"
            :class="heatmapCls(k.total > 0 ? k.errors / k.total : 0)"
            :title="`${k.name}: 错误 ${k.errors}/${k.total}`"
          >
            <span class="max-w-[120px] truncate">{{ k.name }}</span>
            <span class="tabular-nums opacity-70">{{ k.total > 0 ? Math.round((k.errors / k.total) * 100) : 0 }}%</span>
          </div>
        </div>
      </section>

      <!-- 错因分类 -->
      <section v-if="stats.wrong_reasons.length > 0" class="card">
        <h3 class="mb-4 text-sm font-semibold text-slate-800 dark:text-white">
          错因分类分析
          <span class="text-xs font-normal text-slate-400">（共 {{ reasonTotal }} 条）</span>
        </h3>
        <div class="space-y-2.5">
          <div v-for="r in stats.wrong_reasons" :key="r.name" class="flex items-center gap-2">
            <span class="h-3 w-3 shrink-0 rounded-full" :class="REASON_COLORS[r.name] || 'bg-slate-400'"></span>
            <span class="flex-1 text-sm text-slate-700 dark:text-slate-200">{{ r.name }}</span>
            <span class="text-sm font-semibold tabular-nums text-slate-800 dark:text-white">{{ r.count }}</span>
            <span class="w-8 text-right text-xs tabular-nums text-slate-400">{{ Math.round((r.count / reasonTotal) * 100) }}%</span>
            <div class="h-2 w-24 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
              <div
                class="h-full rounded-full"
                :class="REASON_COLORS[r.name] || 'bg-slate-400'"
                :style="{ width: `${(r.count / reasonTotal) * 100}%` }"
              ></div>
            </div>
          </div>
        </div>
      </section>

      <!-- 最近复习历史 -->
      <section v-if="stats.recent.length > 0" class="card !p-0 overflow-hidden">
        <div class="border-b border-slate-100 px-5 py-3 dark:border-slate-800">
          <h3 class="text-sm font-semibold text-slate-800 dark:text-white">
            复习历史
            <span class="ml-1 text-xs font-normal text-slate-400">（最近 {{ stats.recent.length }} 条）</span>
          </h3>
        </div>
        <div class="divide-y divide-slate-50 dark:divide-slate-800/60">
          <div v-for="(log, i) in stats.recent" :key="i" class="flex items-center gap-3 px-5 py-3">
            <span class="w-16 shrink-0 text-[10px] tabular-nums text-slate-400">{{ log.date }}</span>
            <span class="min-w-0 flex-1 truncate text-sm text-slate-700 dark:text-slate-200">
              {{ log.question_content || `题目 ${log.question_id}` }}
            </span>
            <span
              v-if="log.rating"
              class="shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-medium"
              :class="RATING_LABEL[log.rating]?.cls || 'bg-slate-100 text-slate-500'"
            >
              {{ RATING_LABEL[log.rating]?.text || log.rating }}
            </span>
            <span v-if="log.mode" class="hidden shrink-0 text-[9px] text-slate-400 sm:inline">
              {{ MODE_LABEL[log.mode] || log.mode }}
            </span>
          </div>
        </div>
      </section>

      <p v-if="masteryTotal === 0" class="card py-12 text-center text-sm text-slate-400">
        还没有复习记录，开始刷题后这里会显示统计数据。
      </p>
    </template>
  </div>
</template>
