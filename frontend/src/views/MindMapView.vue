<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Loader2, Network, Sparkles, X } from 'lucide-vue-next'
import { knowledgeApi, mindmapApi, workbookApi } from '../api'
import type { KnowledgeSuggestion } from '../api'
import { SYSTEM_WORKBOOK_ID } from '../lib/constants'
import type { MindMapNode, Workbook } from '../types'
import MindMap from '../components/MindMap.vue'

const route = useRoute()
const workbooks = ref<Workbook[]>([])
const selected = ref<number>(SYSTEM_WORKBOOK_ID)
const root = ref<MindMapNode | null>(null)

// ── 选中节点 + AI 扩展 ──
const selectedNode = ref<{ id: number; label: string } | null>(null)
const suggesting = ref(false)
const suggestions = ref<KnowledgeSuggestion[]>([])
const picked = ref<Set<string>>(new Set())
const applying = ref(false)
const errorMsg = ref('')

const builtin: Workbook = {
  id: SYSTEM_WORKBOOK_ID,
  user_id: 0,
  name: '内置题库',
  description: '系统内置参考题库（只读）',
  created_at: '',
  updated_at: '',
}

const options = computed(() => [builtin, ...workbooks.value])
const isBuiltin = computed(() => selected.value === SYSTEM_WORKBOOK_ID)

const loading = ref(false)

async function load() {
  try {
    workbooks.value = await workbookApi.list()
  } catch {
    workbooks.value = []
  }
  const fromQuery = route.query.workbook_id
  selected.value = fromQuery != null ? Number(fromQuery) : SYSTEM_WORKBOOK_ID
  await loadMindmap()
}

async function loadMindmap() {
  loading.value = true
  errorMsg.value = ''
  try {
    const data = await mindmapApi.get(selected.value)
    root.value = data.root
    closePanel()
  } catch (e: any) {
    errorMsg.value = e.message || '导图加载失败'
  } finally {
    loading.value = false
  }
}

function onWorkbookChange() {
  // select @change 显式触发，避免依赖 watch 链路
  loadMindmap()
}

onMounted(load)

// ── 面板交互 ──

function onSelectNode(node: { id: number; label: string }) {
  selectedNode.value = node
  suggestions.value = []
  picked.value = new Set()
  errorMsg.value = ''
}

function closePanel() {
  selectedNode.value = null
  suggestions.value = []
  picked.value = new Set()
  errorMsg.value = ''
}

async function suggest() {
  if (!selectedNode.value) return
  suggesting.value = true
  errorMsg.value = ''
  try {
    const resp = await knowledgeApi.suggestChildren(selectedNode.value.id)
    suggestions.value = resp.suggestions
    picked.value = new Set(resp.suggestions.map((s) => s.name))
  } catch (e: any) {
    errorMsg.value = e.message || '建议生成失败'
  } finally {
    suggesting.value = false
  }
}

function togglePick(name: string) {
  const next = new Set(picked.value)
  if (next.has(name)) next.delete(name)
  else next.add(name)
  picked.value = next
}

async function applySuggestions() {
  if (!selectedNode.value) return
  const chosen = suggestions.value.filter((s) => picked.value.has(s.name))
  if (chosen.length === 0) return

  applying.value = true
  errorMsg.value = ''
  try {
    // 查父节点 level，子节点挂其下
    const nodes = await knowledgeApi.list(selected.value)
    const parent = nodes.find((n) => n.id === selectedNode.value!.id)
    for (const s of chosen) {
      await knowledgeApi.create({
        workbook_id: selected.value,
        parent_id: selectedNode.value.id,
        name: s.name,
        description: s.description,
        level: (parent?.level ?? 0) + 1,
      })
    }
    await loadMindmap()
  } catch (e: any) {
    errorMsg.value = e.message || '入库失败'
  } finally {
    applying.value = false
  }
}

const pickedCount = computed(() => picked.value.size)
</script>

<template>
  <div>
    <h2 class="mb-3 flex items-center gap-2 text-xl font-bold text-slate-800 dark:text-white">
      <Network :size="20" class="text-indigo-500" />
      思维导图
    </h2>
    <select v-model="selected" class="input mb-4 max-w-xs" @change="onWorkbookChange">
      <option v-for="wb in options" :key="wb.id" :value="wb.id">{{ wb.name }}</option>
    </select>

    <p v-if="loading" class="mb-3 text-xs text-slate-400">
      <Loader2 :size="12" class="inline animate-spin mr-1" />加载中…
    </p>
    <p v-if="errorMsg && !selectedNode" class="mb-3 text-xs text-red-500">{{ errorMsg }}</p>

    <div class="flex gap-4 items-start">
      <div class="card flex-1 overflow-auto">
        <!-- :key 强制重建 markmap 实例，绕过 setData diff 问题 -->
        <MindMap
          v-if="root && root.children.length > 0"
          :key="selected"
          :root="root"
          @select="onSelectNode"
        />
        <p v-else-if="!loading" class="text-sm text-slate-400 dark:text-slate-500">
          暂无知识结构。上传资料或使用 AI 助手生成题目后，会自动构建知识树。
        </p>
      </div>

      <!-- 选中节点面板 -->
      <div v-if="selectedNode" class="card w-72 shrink-0 p-4 space-y-3 animate-slide-up">
        <div class="flex items-start justify-between gap-2">
          <div class="min-w-0">
            <p class="text-[11px] text-slate-400 dark:text-slate-500">当前节点</p>
            <p class="text-sm font-semibold text-slate-800 dark:text-white truncate">
              {{ selectedNode.label }}
            </p>
          </div>
          <button class="btn-icon" title="关闭" @click="closePanel">
            <X :size="14" />
          </button>
        </div>

        <!-- AI 扩展按钮 -->
        <button
          v-if="!isBuiltin"
          class="btn-secondary w-full"
          :disabled="suggesting || applying"
          @click="suggest"
        >
          <Loader2 v-if="suggesting" :size="14" class="animate-spin" />
          <Sparkles v-else :size="14" />
          {{ suggesting ? '生成中…' : 'AI 扩展子分支' }}
        </button>
        <p v-else class="text-xs text-slate-400">内置题库为只读，无法扩展</p>

        <p v-if="errorMsg" class="text-xs text-red-500">{{ errorMsg }}</p>

        <!-- 建议列表 -->
        <div v-if="suggestions.length > 0" class="space-y-1.5">
          <p class="text-[11px] text-slate-400 dark:text-slate-500">
            勾选要添加的子知识点（{{ pickedCount }} 个）
          </p>
          <label
            v-for="s in suggestions"
            :key="s.name"
            class="flex items-start gap-2 p-2 rounded-lg border border-slate-100 dark:border-slate-700 hover:border-indigo-200 cursor-pointer"
          >
            <input
              type="checkbox"
              class="mt-0.5 accent-indigo-500"
              :checked="picked.has(s.name)"
              @change="togglePick(s.name)"
            />
            <span class="min-w-0">
              <span class="block text-xs font-medium text-slate-700 dark:text-slate-300">{{ s.name }}</span>
              <span v-if="s.description" class="block text-[11px] text-slate-400 truncate">
                {{ s.description }}
              </span>
            </span>
          </label>
          <button class="btn-primary w-full" :disabled="applying || pickedCount === 0" @click="applySuggestions">
            <Loader2 v-if="applying" :size="14" class="animate-spin" />
            添加 {{ pickedCount }} 个子知识点
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
