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

function nextLabel(next: string | null | undefined): string {
  if (!next) return '——'
  const d = new Date(next)
  if (Number.isNaN(d.getTime())) return '——'
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const diff = Math.round((d.getTime() - today.getTime()) / 86400000)
  if (diff <= 0) return '今天'
  if (diff === 1) return '明天'
  if (diff < 7) return `${diff} 天后`
  if (diff < 30) return `${Math.round(diff / 7)} 周后`
  return `${Math.round(diff / 30)} 月后`
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
