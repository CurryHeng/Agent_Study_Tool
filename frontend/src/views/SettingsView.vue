<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  BookOpen,
  Database,
  Info,
  LogOut,
  Moon,
  Plus,
  RefreshCw,
  Sparkles,
  Sun,
  Trash2,
  User,
  X,
} from 'lucide-vue-next'
import { useAuthStore } from '../stores/auth'
import { useDarkMode } from '../lib/darkMode'
import { workbookApi } from '../api'
import type { Workbook } from '../types'

const auth = useAuthStore()
const router = useRouter()
const { isDark, toggle } = useDarkMode()
const me = ref<{ id: number; username: string; email: string; created_at?: string } | null>(null)
const loading = ref(false)

const workbooks = ref<Workbook[]>([])
const showNewWb = ref(false)
const newWbName = ref('')
const newWbDesc = ref('')
const message = ref<string | null>(null)

function showMsg(msg: string) {
  message.value = msg
  setTimeout(() => (message.value = null), 3000)
}

async function refresh() {
  loading.value = true
  try {
    me.value = await auth.refreshMe()
  } catch {
    // 网络异常时仅用本地缓存信息
  } finally {
    loading.value = false
  }
}

async function logout() {
  await auth.logout()
  router.push('/login')
}

async function loadWorkbooks() {
  try {
    workbooks.value = await workbookApi.list()
  } catch {
    workbooks.value = []
  }
}

async function createWorkbook() {
  if (!newWbName.value.trim()) return
  await workbookApi.create(newWbName.value.trim(), newWbDesc.value.trim() || undefined)
  showNewWb.value = false
  newWbName.value = ''
  newWbDesc.value = ''
  showMsg('练习册已创建')
  await loadWorkbooks()
}

onMounted(() => {
  refresh()
  loadWorkbooks()
})
</script>

<template>
  <div class="space-y-4 animate-fade-in">
    <h2 class="text-xl font-bold text-slate-800 dark:text-white">设置</h2>

    <div v-if="message" class="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm font-medium text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-300 animate-slide-up">
      {{ message }}
    </div>

    <!-- 账号信息 -->
    <section class="card">
      <h3 class="mb-3 flex items-center gap-2 font-semibold text-slate-800 dark:text-white">
        <User :size="16" class="text-emerald-500" />
        账号信息
      </h3>
      <div class="space-y-1.5 text-sm text-slate-600 dark:text-slate-300">
        <p>用户名：<span class="font-medium text-slate-800 dark:text-white">{{ me?.username || auth.user?.username }}</span></p>
        <p>邮箱：<span class="font-medium text-slate-800 dark:text-white">{{ me?.email || auth.user?.email }}</span></p>
        <p v-if="me?.id != null">用户 ID：{{ me.id }}</p>
        <p v-if="me?.created_at">注册时间：{{ me.created_at.slice(0, 10) }}</p>
      </div>
      <div class="mt-4 flex gap-2">
        <button class="btn-secondary !py-1.5 text-xs" :disabled="loading" @click="refresh">
          <RefreshCw :size="13" :class="loading ? 'animate-spin' : ''" />
          {{ loading ? '刷新中…' : '刷新信息' }}
        </button>
        <button class="btn-danger !py-1.5 text-xs" @click="logout">
          <LogOut :size="13" />
          退出登录
        </button>
      </div>
    </section>

    <!-- 外观 -->
    <section class="card">
      <div class="flex items-center justify-between">
        <div>
          <h3 class="flex items-center gap-2 font-semibold text-slate-800 dark:text-white">
            <Sun v-if="isDark" :size="16" class="text-amber-400" />
            <Moon v-else :size="16" class="text-emerald-500" />
            外观
          </h3>
          <p class="mt-1 text-xs text-slate-400">切换亮色 / 暗色模式</p>
        </div>
        <button
          type="button"
          role="switch"
          :aria-checked="isDark"
          class="relative h-7 w-12 shrink-0 rounded-full transition-colors"
          :class="isDark ? 'bg-emerald-600' : 'bg-slate-300'"
          @click="toggle"
        >
          <span class="absolute top-1 h-5 w-5 rounded-full bg-white shadow transition-transform" :class="isDark ? 'translate-x-6' : 'translate-x-1'"></span>
        </button>
      </div>
    </section>

    <!-- 练习册管理 -->
    <section class="card !p-0 divide-y divide-slate-100 dark:divide-slate-800">
      <div class="flex items-center justify-between px-5 py-4">
        <div>
          <h3 class="flex items-center gap-2 font-semibold text-slate-800 dark:text-white">
            <BookOpen :size="16" class="text-emerald-500" />
            练习册管理
          </h3>
          <p class="mt-1 text-xs text-slate-400">每道题目归属于一个练习册</p>
        </div>
        <button class="btn-secondary !py-1.5 text-xs" @click="showNewWb = !showNewWb">
          <Plus :size="13" /> 新建
        </button>
      </div>

      <div v-if="showNewWb" class="space-y-3 bg-slate-50 px-5 py-4 dark:bg-slate-800/40 animate-slide-up">
        <input v-model="newWbName" class="input" placeholder="练习册名称" />
        <input v-model="newWbDesc" class="input" placeholder="描述（可选）" />
        <div class="flex gap-2">
          <button class="btn-primary !py-1.5 text-xs" @click="createWorkbook">创建</button>
          <button class="btn-ghost !py-1.5 text-xs" @click="showNewWb = false; newWbName = ''; newWbDesc = ''">
            <X :size="13" /> 取消
          </button>
        </div>
      </div>

      <div v-for="wb in workbooks" :key="wb.id" class="flex items-center justify-between px-5 py-3 transition hover:bg-slate-50 dark:hover:bg-slate-800/40">
        <div>
          <p class="text-sm font-medium text-slate-700 dark:text-slate-200">{{ wb.name }}</p>
          <p class="mt-0.5 text-xs text-slate-400">{{ wb.description || '无描述' }} · 创建于 {{ wb.created_at?.slice(0, 10) }}</p>
        </div>
      </div>

      <p v-if="workbooks.length === 0" class="px-5 py-6 text-center text-xs text-slate-400">还没有练习册，点击"新建"创建一个。</p>
    </section>

    <!-- 数据管理 -->
    <section class="card">
      <h3 class="mb-2 flex items-center gap-2 font-semibold text-slate-800 dark:text-white">
        <Database :size="16" class="text-emerald-500" />
        数据管理
      </h3>
      <p class="mb-3 text-xs text-slate-400">
        学习数据存储在服务端数据库中。导出/导入备份功能尚未实现，暂不可用。
      </p>
      <div class="flex gap-2">
        <button class="btn-ghost !py-1.5 text-xs opacity-50" disabled>导出备份</button>
        <button class="btn-ghost !py-1.5 text-xs opacity-50" disabled>导入备份</button>
      </div>
    </section>

    <!-- AI 配置 -->
    <section class="card">
      <h3 class="mb-2 flex items-center gap-2 font-semibold text-slate-800 dark:text-white">
        <Sparkles :size="16" class="text-violet-500" />
        AI 功能配置
      </h3>
      <p class="text-xs leading-relaxed text-slate-500 dark:text-slate-400">
        AI 出题与 AI 助手使用服务端 DeepSeek 密钥（在
        <code class="rounded bg-slate-100 px-1 dark:bg-slate-800">backend/.env</code>
        中配置
        <code class="rounded bg-slate-100 px-1 dark:bg-slate-800">DEEPSEEK_API_KEY</code>）。
        若未配置，AI 相关功能会返回错误。
      </p>
    </section>

    <!-- 关于 -->
    <section class="card">
      <h3 class="mb-2 flex items-center gap-2 font-semibold text-slate-800 dark:text-white">
        <Info :size="16" class="text-emerald-500" />
        关于
      </h3>
      <p class="text-sm font-medium text-slate-700 dark:text-slate-200">EStudy 智能题库与学习系统</p>
      <p class="text-xs text-slate-400">版本 0.1.0（P0 完善阶段）</p>
      <p class="mt-2 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
        面向大学生期末复习：上传资料 → 生成知识结构/思维导图/题库 → 刷题与错题记录形成学习闭环。
      </p>
      <p class="mt-2 text-xs text-slate-400">
        技术栈：Vue 3 + Vite · FastAPI · LangGraph · SQLite · Chroma · DeepSeek
      </p>
    </section>
  </div>
</template>
