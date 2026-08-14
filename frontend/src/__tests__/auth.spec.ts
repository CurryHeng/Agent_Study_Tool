import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from '../stores/auth'

vi.mock('../api', () => ({
  authApi: {
    login: vi.fn(async () => ({
      user: { id: 1, username: 'alice', email: 'alice@example.com' },
      access_token: 'access',
      refresh_token: 'refresh',
    })),
  },
}))

describe('auth store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('login sets user and loggedIn', async () => {
    const auth = useAuthStore()
    expect(auth.loggedIn).toBe(false)
    await auth.login('alice@example.com', 'password123')
    expect(auth.loggedIn).toBe(true)
    expect(auth.user?.username).toBe('alice')
  })

  it('logout clears user', () => {
    const auth = useAuthStore()
    auth.logout()
    expect(auth.loggedIn).toBe(false)
    expect(auth.user).toBeNull()
  })
})
