<script setup lang="ts">
import { computed } from 'vue'
import type { ActivityDay } from '../types'

const props = defineProps<{ days: ActivityDay[] }>()

const TOTAL_DAYS = 365
const CELL = 12
const GAP = 3
const STEP = CELL + GAP
const LABEL_OFFSET = 26
const TOP_OFFSET = 18

function toDateStr(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const dataMap = computed(() => {
  const map = new Map<string, ActivityDay>()
  for (const d of props.days) map.set(d.date, d)
  return map
})

const cells = computed(() => {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const start = new Date(today)
  start.setDate(start.getDate() - (TOTAL_DAYS - 1))

  // 以周一为列起点（中文习惯），前补到最近的周一
  const firstDow = start.getDay()
  const offsetToMonday = (firstDow + 6) % 7
  const gridStart = new Date(start)
  gridStart.setDate(gridStart.getDate() - offsetToMonday)

  const list: Array<{ date: Date; dayStr: string; inRange: boolean; data: ActivityDay | null }> = []
  const cursor = new Date(gridStart)
  const end = new Date(today)
  end.setDate(end.getDate() + 1)
  while (cursor < end) {
    const dayStr = toDateStr(cursor)
    const inRange = cursor >= start
    list.push({
      date: new Date(cursor),
      dayStr,
      inRange,
      data: inRange ? (dataMap.value.get(dayStr) ?? null) : null,
    })
    cursor.setDate(cursor.getDate() + 1)
  }
  return list
})

const totalCols = computed(() => Math.ceil(cells.value.length / 7))
const W = computed(() => LABEL_OFFSET + totalCols.value * STEP)
const H = computed(() => TOP_OFFSET + 7 * STEP)

const monthLabels = computed(() => {
  const labels: Array<{ col: number; label: string }> = []
  let lastMonth = -1
  for (let col = 0; col < totalCols.value; col++) {
    const idx = col * 7
    if (idx >= cells.value.length) break
    const m = cells.value[idx].date.getMonth()
    if (m !== lastMonth) {
      labels.push({ col, label: `${m + 1}月` })
      lastMonth = m
    }
  }
  return labels
})

const weekLabels = [
  { row: 0, label: '一' },
  { row: 2, label: '三' },
  { row: 4, label: '五' },
]

function levelFor(total: number): 0 | 1 | 2 | 3 | 4 {
  if (total <= 0) return 0
  if (total < 5) return 1
  if (total < 10) return 2
  if (total < 20) return 3
  return 4
}

// emerald 5 档，GitHub 风格；暗色背景下依旧清晰
const LEVEL_COLORS: Record<0 | 1 | 2 | 3 | 4, string> = {
  0: 'rgba(16, 185, 129, 0.08)',
  1: 'rgba(16, 185, 129, 0.35)',
  2: 'rgba(16, 185, 129, 0.55)',
  3: 'rgba(16, 185, 129, 0.80)',
  4: 'rgba(16, 185, 129, 1)',
}

const summary = computed(() => {
  let total = 0
  let correct = 0
  for (const d of props.days) {
    total += d.total
    correct += d.correct
  }
  const activeDays = props.days.filter((d) => d.total > 0).length
  const accuracy = total > 0 ? Math.round((correct / total) * 100) : 0
  return { total, correct, activeDays, accuracy }
})

function xFor(col: number): number {
  return LABEL_OFFSET + col * STEP
}

function yFor(row: number): number {
  return TOP_OFFSET + row * STEP
}
</script>

<template>
  <div class="space-y-3">
    <div class="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500 dark:text-slate-400">
      <div class="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span class="font-semibold text-slate-700 dark:text-slate-200">
          近 365 天 · 共答题 {{ summary.total }} 题
        </span>
        <span class="tabular-nums">活跃 {{ summary.activeDays }} 天</span>
        <span class="tabular-nums">正确率 {{ summary.accuracy }}%</span>
      </div>
      <div class="flex items-center gap-1">
        <span>少</span>
        <span
          v-for="level in 5"
          :key="level"
          class="h-3 w-3 rounded-[3px]"
          :style="{ backgroundColor: LEVEL_COLORS[(level - 1) as 0 | 1 | 2 | 3 | 4] }"
        ></span>
        <span>多</span>
      </div>
    </div>

    <div class="overflow-x-auto pb-1">
      <svg
        :width="W"
        :height="H"
        :viewBox="`0 0 ${W} ${H}`"
        class="min-w-[620px]"
        role="img"
        aria-label="近 365 天学习活跃热力图"
      >
        <!-- 月份标签 -->
        <g v-for="(m, i) in monthLabels" :key="`m${i}`">
          <text
            :x="xFor(m.col)"
            :y="TOP_OFFSET - 6"
            class="fill-slate-400 text-[10px]"
          >
            {{ m.label }}
          </text>
        </g>

        <!-- 周标签 -->
        <g v-for="w in weekLabels" :key="w.row">
          <text
            :x="LABEL_OFFSET - 6"
            :y="yFor(w.row) + CELL / 2 + 3"
            text-anchor="end"
            class="fill-slate-400 text-[10px]"
          >
            {{ w.label }}
          </text>
        </g>

        <!-- 格子 -->
        <g v-for="(cell, i) in cells" :key="`c${i}`">
          <rect
            v-if="cell.inRange"
            :x="xFor(Math.floor(i / 7))"
            :y="yFor(i % 7)"
            :width="CELL"
            :height="CELL"
            rx="3"
            :fill="LEVEL_COLORS[levelFor(cell.data?.total ?? 0)]"
          >
            <title>
              {{ cell.dayStr }}：{{ cell.data?.total ?? 0 }} 题 · 正确 {{ cell.data?.correct ?? 0 }}
            </title>
          </rect>
        </g>
      </svg>
    </div>
  </div>
</template>
