import { defineStore } from 'pinia'
import { ref } from 'vue'
import { clearAuth, getStoredUser, isAuthenticated } from '../api/client'
import { authApi } from '../api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(getStoredUser())
  const loggedIn = ref(isAuthenticated())

  async function login(email: string, password: string) {
    const data = await authApi.login(email, password)
    user.value = data.user
    loggedIn.value = true
  }

  async function register(username: string, email: string, password: string) {
    const data = await authApi.register(username, email, password)
    user.value = data.user
    loggedIn.value = true
  }

  async function logout() {
    try {
      await authApi.logout()
    } catch {
      // 忽略登出网络错误，本地仍清除
    }
    clearAuth()
    user.value = null
    loggedIn.value = false
  }

  async function refreshMe() {
    const me = await authApi.me()
    user.value = me
    return me
  }

  return { user, loggedIn, login, register, logout, refreshMe }
})
