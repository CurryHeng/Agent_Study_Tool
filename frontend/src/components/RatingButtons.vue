<script setup lang="ts">
defineProps<{
  allowed?: string[]
  nextReview?: string | null
}>()
defineEmits<{ (e: 'rate', rating: string): void }>()

const ratings = [
  { key: 'again', label: '忘记', desc: '完全不会', color: 'bg-rose-500 hover:bg-rose-600', shortcut: '1' },
  { key: 'hard', label: '困难', desc: '想起来了但费劲', color: 'bg-orange-400 hover:bg-orange-500', shortcut: '2' },
  { key: 'good', label: '正确', desc: '正常回忆起', color: 'bg-emerald-500 hover:bg-emerald-600', shortcut: '3' },
  { key: 'easy', label: '简单', desc: '非常轻松', color: 'bg-blue-500 hover:bg-blue-600', shortcut: '4' },
]

function nextLabel(due: string | null | undefined): string {
  if (!due) return '——'
  // FSRS due 为 naive UTC datetime，补 Z 再解析为本地时间
  const d = new Date(/Z|[+-]\d{2}:?\d{2}$/.test(due) ? due : due.replace(' ', 'T') + 'Z')
  if (Number.isNaN(d.getTime())) return '——'
  const diffSec = (d.getTime() - Date.now()) / 1000
  if (diffSec <= 0) return '现在'
  if (diffSec < 3600) return `${Math.max(1, Math.round(diffSec / 60))} 分钟后`
  if (diffSec < 86400) return `${Math.round(diffSec / 3600)} 小时后`
  const days = Math.round(diffSec / 86400)
  if (days < 7) return `${days} 天后`
  if (days < 30) return `${Math.round(days / 7)} 周后`
  return `${Math.round(days / 30)} 月后`
}
</script>

<template>
  <div class="space-y-2">
    <p class="text-center text-xs text-slate-400">评价你的掌握程度</p>
    <div class="grid grid-cols-4 gap-2">
      <button
        v-for="r in ratings.filter((x) => !allowed || allowed.includes(x.key))"
        :key="r.key"
        :class="r.color"
        class="flex flex-col items-center gap-0.5 rounded-xl px-2 py-2.5 text-white shadow-sm transition active:scale-95"
        @click="$emit('rate', r.key)"
      >
        <span class="text-sm font-bold">{{ r.label }}</span>
        <span class="text-[10px] leading-tight opacity-80">{{ r.desc }}</span>
        <span class="mt-0.5 text-[9px] opacity-50">{{ r.shortcut }}</span>
      </button>
    </div>
    <p class="text-center text-[10px] text-slate-400">下次复习：{{ nextLabel(nextReview) }}</p>
  </div>
</template>
