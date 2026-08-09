const API_BASE = '/api'

const ACCESS_TOKEN_KEY = 'quiz-app-access-token'
const REFRESH_TOKEN_KEY = 'quiz-app-refresh-token'
const USER_KEY = 'quiz-app-user'

let accessToken: string | null = localStorage.getItem(ACCESS_TOKEN_KEY) || null
let refreshToken: string | null = localStorage.getItem(REFRESH_TOKEN_KEY) || null
let refreshPromise: Promise<boolean> | null = null
let onAuthChange: (() => void) | null = null

export function setAuthChangeHandler(handler: () => void) {
  onAuthChange = handler
}

export function getStoredUser(): { id: string; username: string; email: string } | null {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function getAccessToken(): string | null {
  return accessToken
}

export function isAuthenticated(): boolean {
  return !!accessToken
}

async function doRefresh(): Promise<boolean> {
  if (!refreshToken) return false
  try {
    const resp = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refreshToken }),
    })
    if (!resp.ok) {
      clearAuth()
      return false
    }
    const data = await resp.json()
    accessToken = data.accessToken
    refreshToken = data.refreshToken
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken!)
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken!)
    return true
  } catch {
    return false
  }
}

async function getValidAccessToken(): Promise<string | null> {
  if (accessToken) return accessToken
  if (!refreshToken) return null

  if (!refreshPromise) {
    refreshPromise = doRefresh().finally(() => { refreshPromise = null })
  }
  const ok = await refreshPromise
  return ok ? accessToken : null
}

export function clearAuth() {
  accessToken = null
  refreshToken = null
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
  if (onAuthChange) onAuthChange()
}

export function setAuth(access: string, refresh: string, user: { id: string; username: string; email: string }) {
  accessToken = access
  refreshToken = refresh
  localStorage.setItem(ACCESS_TOKEN_KEY, access)
  localStorage.setItem(REFRESH_TOKEN_KEY, refresh)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
  if (onAuthChange) onAuthChange()
}

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export async function request(method: string, path: string, body?: any): Promise<any> {
  const token = await getValidAccessToken()

  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`

  try {
    const resp = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    })

    if (resp.status === 401) {
      // Try refresh once
      if (refreshToken) {
        const refreshed = await doRefresh()
        if (refreshed) {
          // Retry with new token
          headers['Authorization'] = `Bearer ${accessToken}`
          const retryResp = await fetch(`${API_BASE}${path}`, {
            method,
            headers,
            body: body ? JSON.stringify(body) : undefined,
          })
          if (retryResp.ok) {
            const ct = retryResp.headers.get('content-type')
            return ct && ct.includes('application/json') ? retryResp.json() : retryResp
          }
          const errData = await retryResp.json().catch(() => ({}))
          throw new ApiError(errData.error || '请求失败', retryResp.status)
        }
      }
      clearAuth()
      throw new ApiError('登录已过期，请重新登录', 401)
    }

    if (!resp.ok) {
      const errData = await resp.json().catch(() => ({}))
      throw new ApiError(errData.error || '请求失败', resp.status)
    }

    const ct = resp.headers.get('content-type')
    if (ct && ct.includes('application/json')) {
      return resp.json()
    }
    return resp
  } catch (err: any) {
    if (err instanceof ApiError) throw err
    // Network error — offline
    throw new ApiError('网络不可用', 0)
  }
}

// Auth API
export const auth = {
  register: (username: string, email: string, password: string) =>
    request('POST', '/auth/register', { username, email, password }),
  login: (email: string, password: string) =>
    request('POST', '/auth/login', { email, password }),
  refresh: () => request('POST', '/auth/refresh', { refreshToken }),
  logout: () => request('POST', '/auth/logout', { refreshToken }),
  me: () => request('GET', '/auth/me'),
}

// Questions API
export const questionsApi = {
  list: () => request('GET', '/questions'),
  create: (data: any) => request('POST', '/questions', data),
  update: (id: string, data: any) => request('PUT', `/questions/${id}`, data),
  delete: (id: string) => request('DELETE', `/questions/${id}`),
}

// Cards API
export const cardsApi = {
  list: () => request('GET', '/cards'),
  update: (questionId: string, data: any) => request('PUT', `/cards/${questionId}`, data),
  toggleFavorite: (questionId: string) => request('PUT', `/cards/${questionId}/favorite`),
}

// Logs API
export const logsApi = {
  list: (since?: string) => request('GET', `/logs${since ? `?since=${encodeURIComponent(since)}` : ''}`),
  create: (data: any) => request('POST', '/logs', data),
}

// Workbooks API
export const workbooksApi = {
  list: () => request('GET', '/workbooks'),
  create: (name: string, description?: string) => request('POST', '/workbooks', { name, description }),
}

// Sync API
export const syncApi = {
  push: (clientData: any) => request('POST', '/sync', { clientData }),
}
