import { useEffect, useState, createContext, useContext } from 'react'
import { Routes, Route, NavLink, useLocation, Link } from 'react-router-dom'
import { BookOpen, LayoutDashboard, BarChart3, Settings, User, LogOut, Sun, Moon } from 'lucide-react'
import Dashboard from './components/Dashboard'
import QuizSession from './components/QuizSession'
import StrictSession from './components/StrictSession'
import QuestionList from './components/QuestionList'
import AddQuestion from './components/AddQuestion'
import Stats from './components/Stats'
import SettingsPage from './components/SettingsPage'
import LoginPage from './components/LoginPage'
import RegisterPage from './components/RegisterPage'
import { migrateUserQuestions } from './lib/storage'
import { getStoredUser, isAuthenticated, clearAuth, setAuthChangeHandler, auth } from './api/client'
import { useDarkMode } from './lib/useDarkMode'

interface AuthState {
  user: { id: string; username: string; email: string } | null
  loggedIn: boolean
  logout: () => void
}

export const AuthContext = createContext<AuthState>({
  user: null,
  loggedIn: false,
  logout: () => {},
})

export function useAuth() {
  return useContext(AuthContext)
}

export default function App() {
  const location = useLocation()
  const [user, setUser] = useState(getStoredUser())
  const [loggedIn, setLoggedIn] = useState(isAuthenticated())
  const [dark, toggleDark] = useDarkMode()

  useEffect(() => {
    migrateUserQuestions()
    // No longer pre-set API key — user sets via Settings page which calls backend
  }, [])

  useEffect(() => {
    setAuthChangeHandler(() => {
      setUser(getStoredUser())
      setLoggedIn(isAuthenticated())
      // Force re-render
    })
  }, [])

  // Try to restore session on mount
  useEffect(() => {
    if (!loggedIn) {
      auth.refresh().then((data: any) => {
        if (data?.accessToken) {
          // Session restored
          setLoggedIn(true)
          setUser(getStoredUser())
        }
      }).catch(() => {
        // No valid session, stay logged out
      })
    }
  }, [])

  const handleLogout = () => {
    auth.logout().catch(() => {})
    clearAuth()
    setUser(null)
    setLoggedIn(false)
  }

  // Smart nav: if user has active quiz session, "复习" goes back to it
  const getReviewLink = () => {
    try {
      const raw = localStorage.getItem('quiz-session-last')
      if (raw) {
        const s = JSON.parse(raw)
        if (s.mode && s.cards?.length > 0) return `/review?mode=${s.mode}`
      }
    } catch { /* ignore */ }
    return '/'
  }

  return (
    <AuthContext.Provider value={{ user, loggedIn, logout: handleLogout }}>
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50">
        <header className="sticky top-0 z-50 glass border-b border-slate-200/40">
          <div className="max-w-4xl mx-auto px-4 h-14 flex items-center justify-between">
            <NavLink to="/" className="flex items-center gap-2.5 font-bold text-lg text-slate-800 no-underline">
              <span className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center text-white text-sm">
                Ag
              </span>
              Agent 题库
            </NavLink>
            <nav className="flex items-center gap-0.5">
              <NavLink
                to={getReviewLink()}
                className={({ isActive }) =>
                  `flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 no-underline ${
                    isActive || location.pathname.startsWith('/review') ? 'bg-indigo-50 text-indigo-700' : 'text-slate-500 hover:text-slate-700 hover:bg-slate-100'
                  }`}
              >
                <LayoutDashboard size={17} />
                <span className="hidden sm:inline">复习</span>
              </NavLink>
              <NavItem to="/questions" icon={<BookOpen size={17} />} label="题库" />
              <NavItem to="/stats" icon={<BarChart3 size={17} />} label="统计" />
              <NavItem to="/settings" icon={<Settings size={17} />} label="设置" />
              <button
                onClick={toggleDark}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-sm text-slate-500 hover:text-slate-700 hover:bg-slate-100 transition-all duration-200"
                title={dark ? '切换浅色模式' : '切换深色模式'}
              >
                {dark ? <Sun size={17} /> : <Moon size={17} />}
              </button>
              {loggedIn ? (
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-slate-500 hover:text-slate-700 hover:bg-slate-100 transition-all duration-200 ml-1"
                  title={`当前用户: ${user?.username}`}
                >
                  <User size={17} />
                  <span className="hidden sm:inline text-xs max-w-[60px] truncate">{user?.username}</span>
                  <LogOut size={14} className="hidden sm:inline text-slate-400" />
                </button>
              ) : (
                <Link
                  to="/login"
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-indigo-600 hover:bg-indigo-50 transition-all duration-200 no-underline ml-1"
                >
                  <User size={17} />
                  <span className="hidden sm:inline">登录</span>
                </Link>
              )}
            </nav>
          </div>
        </header>
        <main className="max-w-3xl mx-auto px-4 py-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/review" element={<QuizSession key={location.key} />} />
            <Route path="/strict" element={<StrictSession key={location.key + '-strict'} />} />
            <Route path="/questions" element={<QuestionList />} />
            <Route path="/questions/add" element={<AddQuestion />} />
            <Route path="/stats" element={<Stats />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
          </Routes>
        </main>
      </div>
    </AuthContext.Provider>
  )
}

function NavItem({ to, icon, label }: { to: string; icon: React.ReactNode; label: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 no-underline ${
          isActive ? 'bg-indigo-50 text-indigo-700' : 'text-slate-500 hover:text-slate-700 hover:bg-slate-100'
        }`
      }
    >
      {icon}
      <span className="hidden sm:inline">{label}</span>
    </NavLink>
  )
}
