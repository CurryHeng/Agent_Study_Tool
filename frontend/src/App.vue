<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  BarChart3,
  BookX,
  GraduationCap,
  History,
  Home,
  Library,
  LogOut,
  Moon,
  Network,
  Settings,
  Sparkles,
  Sun,
} from 'lucide-vue-next'
import { useAuthStore } from './stores/auth'
import { useDarkMode } from './lib/darkMode'

const auth = useAuthStore()
const router = useRouter()
const { isDark, toggle } = useDarkMode()

const initial = computed(() => (auth.user?.username || '?').charAt(0).toUpperCase())

const navItems = [
  { to: '/', label: '首页', icon: Home },
  { to: '/questions', label: '题库', icon: Library },
  { to: '/stats', label: '统计', icon: BarChart3 },
  { to: '/history', label: '时间线', icon: History },
  { to: '/mindmap', label: '可视化', icon: Network },
  { to: '/wrong', label: '错题本', icon: BookX },
  { to: '/assistant', label: '智能助手', icon: Sparkles },
  { to: '/settings', label: '设置', icon: Settings },
]

async function logout() {
  await auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50/60 dark:from-slate-950 dark:via-slate-950 dark:to-indigo-950/40">
    <header
      v-if="auth.loggedIn"
      class="glass sticky top-0 z-50 border-b border-slate-200/60 dark:border-slate-800/60"
    >
      <div class="mx-auto flex h-14 max-w-6xl items-center justify-between gap-3 px-4">
        <RouterLink to="/" class="flex shrink-0 items-center gap-2.5 font-bold text-slate-800 no-underline dark:text-white">
          <span
            class="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 text-white shadow-lg shadow-emerald-500/25"
          >
            <GraduationCap :size="18" />
          </span>
          <span class="text-base tracking-tight">EStudy</span>
        </RouterLink>

        <nav class="flex items-center gap-0.5 overflow-x-auto">
          <RouterLink v-for="item in navItems" :key="item.to" :to="item.to" class="nav-link">
            <component :is="item.icon" :size="16" />
            <span class="hidden sm:inline">{{ item.label }}</span>
          </RouterLink>
        </nav>

        <div class="flex shrink-0 items-center gap-1">
          <button class="btn-icon" :aria-label="isDark ? '切换到亮色模式' : '切换到暗色模式'" @click="toggle">
            <Sun v-if="isDark" :size="18" />
            <Moon v-else :size="18" />
          </button>
          <div class="ml-1 flex items-center gap-1.5 border-l border-slate-200 pl-2 dark:border-slate-800">
            <span
              class="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 text-xs font-bold text-white"
            >
              {{ initial }}
            </span>
            <button class="btn-icon" title="退出登录" @click="logout">
              <LogOut :size="17" />
            </button>
          </div>
        </div>
      </div>
    </header>
    <main class="mx-auto max-w-5xl px-4 py-6 sm:py-8">
      <RouterView />
    </main>
  </div>
</template>
