<script setup lang="ts">
defineProps<{
  page: number
  pageSize: number
  hasMore: boolean
}>()

const emit = defineEmits<{
  (e: 'prev'): void
  (e: 'next'): void
}>()
</script>

<template>
  <div class="mt-4 flex items-center justify-center gap-2">
    <button class="btn-secondary !py-1.5 text-xs" :disabled="page <= 1" @click="emit('prev')">上一页</button>
    <span class="text-xs text-slate-400">第 {{ page }} 页</span>
    <button class="btn-secondary !py-1.5 text-xs" :disabled="!hasMore" @click="emit('next')">下一页</button>
  </div>
</template>
