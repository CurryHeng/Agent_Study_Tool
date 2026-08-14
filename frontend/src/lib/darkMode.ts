import { ref, watchEffect } from 'vue'

const STORAGE_KEY = 'studyforge-theme'

const isDark = ref(
  typeof localStorage !== 'undefined' && localStorage.getItem(STORAGE_KEY) === 'dark',
)

watchEffect(() => {
  document.documentElement.classList.toggle('dark', isDark.value)
})

export function useDarkMode() {
  function toggle() {
    isDark.value = !isDark.value
    localStorage.setItem(STORAGE_KEY, isDark.value ? 'dark' : 'light')
  }
  return { isDark, toggle }
}
