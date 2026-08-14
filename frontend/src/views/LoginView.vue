<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { AlertCircle, GraduationCap, Loader2, LogIn } from 'lucide-vue-next'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(email.value, password.value)
    router.push('/')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="flex min-h-[70vh] items-center justify-center">
    <div class="w-full max-w-sm animate-slide-up">
      <div class="mb-8 text-center">
        <div
          class="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-lg shadow-indigo-500/30"
        >
          <GraduationCap :size="26" />
        </div>
        <h1 class="text-2xl font-bold tracking-tight text-slate-800 dark:text-white">StudyForge</h1>
        <p class="mt-1 text-sm text-slate-400">欢迎回来，继续你的学习之旅</p>
      </div>

      <form class="card space-y-4 p-6" @submit.prevent="submit">
        <div
          v-if="error"
          class="flex items-center gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2.5 text-sm text-rose-600 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-400"
        >
          <AlertCircle :size="15" />
          <span>{{ error }}</span>
        </div>

        <div>
          <label class="label" for="email">邮箱</label>
          <input id="email" v-model="email" type="email" class="input" placeholder="example@email.com" required />
        </div>
        <div>
          <label class="label" for="password">密码</label>
          <input id="password" v-model="password" type="password" class="input" placeholder="••••••••" required />
        </div>

        <button class="btn-primary w-full" type="submit" :disabled="loading">
          <Loader2 v-if="loading" :size="16" class="animate-spin" />
          <LogIn v-else :size="16" />
          登录
        </button>

        <p class="text-center text-sm text-slate-500 dark:text-slate-400">
          还没有账号？
          <RouterLink to="/register" class="font-medium text-indigo-600 hover:underline dark:text-indigo-400">注册</RouterLink>
        </p>
      </form>
    </div>
  </div>
</template>
