import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { LogIn, Loader2, AlertCircle } from 'lucide-react'
import { auth, setAuth } from '../api/client'
import { pullAllFromServer } from '../lib/storage'

export default function LoginPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim() || !password) {
      setError('请填写邮箱和密码')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const data = await auth.login(email.trim(), password)
      setAuth(data.accessToken, data.refreshToken, data.user)
      await pullAllFromServer()
      navigate('/')
    } catch (err: any) {
      setError(err.message || '登录失败')
    } finally {
      setLoading(false)
    }
  }

  const devLogin = async () => {
    setLoading(true)
    setError(null)
    try {
      // Try register first (idempotent — fails if exists), then login
      try { await auth.register('dev', 'dev@local.test', '12345678') } catch { /* already exists */ }
      const data = await auth.login('dev@local.test', '12345678')
      setAuth(data.accessToken, data.refreshToken, data.user)
      await pullAllFromServer()
      navigate('/')
    } catch (err: any) {
      setError(err.message || '开发者登录失败，请确认后端已启动')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-[70vh] flex items-center justify-center">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-2xl font-bold mx-auto mb-4">
            Ag
          </div>
          <h1 className="text-xl font-bold text-slate-800">Agent 题库</h1>
          <p className="text-sm text-slate-400 mt-1">登录以跨设备同步数据</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
          {error && (
            <div className="flex items-center gap-2 px-3 py-2.5 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
              <AlertCircle size={15} />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-500 mb-1.5">邮箱</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="example@email.com"
              autoFocus
              className="w-full px-3 py-2.5 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-500 mb-1.5">密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="至少 8 个字符"
              className="w-full px-3 py-2.5 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 text-sm font-semibold text-white bg-indigo-600 rounded-xl hover:bg-indigo-700 disabled:opacity-50 transition-all active:scale-[0.98] flex items-center justify-center gap-2"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <LogIn size={16} />}
            登录
          </button>

          <div className="text-center text-xs text-slate-400 space-y-2">
            <p>
              还没有账号？<Link to="/register" className="text-indigo-500 hover:underline">注册</Link>
            </p>
            <p>
              <Link to="/" className="text-slate-400 hover:text-slate-600">跳过，离线使用</Link>
            </p>
            <div className="pt-2 border-t border-slate-100">
              <button type="button" onClick={devLogin} disabled={loading}
                className="text-xs text-slate-400 hover:text-indigo-500 transition-colors">
                🔧 开发者登录（密码 123）
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}
