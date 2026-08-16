<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import MindMapView from './MindMapView.vue'
import KnowledgeGraphView from './KnowledgeGraphView.vue'

const route = useRoute()
const router = useRouter()

const activeTab = computed(() => {
  const tab = route.query.tab
  return tab === 'graph' ? 'graph' : 'mindmap'
})

function switchTab(tab: string) {
  router.replace({ path: '/visualization', query: { tab } })
}
</script>

<template>
  <div class="space-y-4 animate-fade-in">
    <div class="flex items-center gap-2 border-b border-slate-200 pb-2 dark:border-slate-800">
      <button
        class="rounded-lg px-3 py-1.5 text-sm font-medium transition"
        :class="activeTab === 'mindmap' ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-300' : 'text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800'"
        @click="switchTab('mindmap')"
      >
        思维导图
      </button>
      <button
        class="rounded-lg px-3 py-1.5 text-sm font-medium transition"
        :class="activeTab === 'graph' ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-300' : 'text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800'"
        @click="switchTab('graph')"
      >
        知识图谱
      </button>
    </div>

    <MindMapView v-if="activeTab === 'mindmap'" />
    <KnowledgeGraphView v-else />
  </div>
</template>
