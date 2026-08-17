const ACCESS_KEY = 'studyforge-access-token'
const REFRESH_KEY = 'studyforge-refresh-token'
const USER_KEY = 'studyforge-user'

let accessToken: string | null = localStorage.getItem(ACCESS_KEY)
let refreshToken: string | null = localStorage.getItem(REFRESH_KEY)

export function getAccessToken(): string | null {
  return accessToken
}

export function getRefreshToken(): string | null {
  return refreshToken
}

export function isAuthenticated(): boolean {
  return !!accessToken
}

export function getStoredUser(): { id: number; username: string; email: string } | null {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function setAuth(access: string, refresh: string, user: { id: number; username: string; email: string }) {
  accessToken = access
  refreshToken = refresh
  localStorage.setItem(ACCESS_KEY, access)
  localStorage.setItem(REFRESH_KEY, refresh)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export const AUTH_INVALID_EVENT = 'estudy:auth-invalid'

export function clearAuth() {
  accessToken = null
  refreshToken = null
  localStorage.removeItem(ACCESS_KEY)
  localStorage.removeItem(REFRESH_KEY)
  localStorage.removeItem(USER_KEY)
  // 通知 auth store 同步（修复：令牌过期/刷新失败时 loggedIn 不更新的问题）
  window.dispatchEvent(new CustomEvent(AUTH_INVALID_EVENT))
}

async function doRefresh(): Promise<boolean> {
  if (!refreshToken) return false
  const resp = await fetch('/api/auth/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  })
  if (!resp.ok) {
    clearAuth()
    return false
  }
  const data = await resp.json()
  accessToken = data.access_token
  refreshToken = data.refresh_token
  localStorage.setItem(ACCESS_KEY, accessToken!)
  localStorage.setItem(REFRESH_KEY, refreshToken!)
  return true
}

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

const DEFAULT_TIMEOUT_MS = 120_000  // LLM 端点最长可达数十秒；超时终止等待并提示

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (accessToken) headers['Authorization'] = `Bearer ${accessToken}`

  const doFetch = () => {
    const ctrl = new AbortController()
    const timer = setTimeout(() => ctrl.abort(), DEFAULT_TIMEOUT_MS)
    const p = fetch(`/api${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal: ctrl.signal,
    })
    p.finally(() => clearTimeout(timer))
    return p
  }

  let resp: Response
  try {
    resp = await doFetch()
  } catch (err: any) {
    if (err?.name === 'AbortError') throw new ApiError('请求超时，请重试', 0)
    throw new ApiError('网络不可用', 0)
  }

  if (resp.status === 401 && refreshToken) {
    const refreshed = await doRefresh()
    if (refreshed) {
      headers['Authorization'] = `Bearer ${accessToken}`
      resp = await doFetch()
    }
  }

  if (!resp.ok) {
    const errData = await resp.json().catch(() => ({}))
    throw new ApiError(errData.detail || '请求失败', resp.status)
  }

  if (resp.status === 204) return undefined as T
  return (await resp.json()) as T
}

async function requestForm<T>(method: string, path: string, form: FormData): Promise<T> {
  const headers: Record<string, string> = {}
  if (accessToken) headers['Authorization'] = `Bearer ${accessToken}`

  const doFetch = () => {
    const ctrl = new AbortController()
    const timer = setTimeout(() => ctrl.abort(), DEFAULT_TIMEOUT_MS)
    const p = fetch(`/api${path}`, {
      method,
      headers,
      body: form,
      signal: ctrl.signal,
    })
    p.finally(() => clearTimeout(timer))
    return p
  }

  let resp: Response
  try {
    resp = await doFetch()
  } catch (err: any) {
    if (err?.name === 'AbortError') throw new ApiError('请求超时，请重试', 0)
    throw new ApiError('网络不可用', 0)
  }

  if (resp.status === 401 && refreshToken) {
    const refreshed = await doRefresh()
    if (refreshed) {
      headers['Authorization'] = `Bearer ${accessToken}`
      resp = await doFetch()
    }
  }

  if (!resp.ok) {
    const errData = await resp.json().catch(() => ({}))
    throw new ApiError(errData.detail || '请求失败', resp.status)
  }

  return (await resp.json()) as T
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body),
  put: <T>(path: string, body?: unknown) => request<T>('PUT', path, body),
  del: <T>(path: string) => request<T>('DELETE', path),
  postForm: <T>(path: string, form: FormData) => requestForm<T>('POST', path, form),
}

/** XHR 上传（带实时进度回调）。 */
export function uploadWithProgress<T>(
  path: string,
  form: FormData,
  onProgress: (pct: number) => void,
): Promise<T> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `/api${path}`)
    if (accessToken) xhr.setRequestHeader('Authorization', `Bearer ${accessToken}`)
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100))
    }
    xhr.onload = () => {
      let data: Record<string, unknown>
      try {
        data = JSON.parse(xhr.responseText)
      } catch {
        data = {}
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(data as T)
      } else {
        reject(new ApiError((data.detail as string) || '上传失败', xhr.status))
      }
    }
    xhr.onerror = () => reject(new ApiError('网络错误，上传失败', 0))
    xhr.send(form)
  })
}
