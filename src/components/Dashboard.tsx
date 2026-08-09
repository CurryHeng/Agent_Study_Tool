import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Play, TrendingUp, Calendar, Zap, ChevronRight, ListFilter, Check, Timer, Target, Sparkles, Star } from 'lucide-react'
import questionsData from '../data/questions.json'
import type { Question, ReviewCard } from '../types'
import { loadCards, saveCards, getStats, loadUserQuestions, sortChapterEntries, pullAllFromServer } from '../lib/storage'
import { isAuthenticated } from '../api/client'
import { createCard } from '../lib/sm2'
import { useAppStore } from '../lib/store'

export default function Dashboard() {
  const navigate = useNavigate()
  const store = useAppStore()
  const [showPicker, setShowPicker] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [expandedChapters, setExpandedChapters] = useState<Set<string>>(new Set())
  const [showModeModal, setShowModeModal] = useState(false)

  // Check for saved quiz session (so user can resume)
  const savedSession = useMemo(() => {
    try {
      const raw = localStorage.getItem('quiz-session-last')
      if (!raw) return null
      const parsed = JSON.parse(raw)
      if (parsed.cards?.length > 0 && parsed.mode) return parsed
    } catch { /* ignore */ }
    return null
  }, [])

  // Re-compute on every render so newly added user questions appear
  const questions: Question[] = [...questionsData, ...store.userQuestions]

  // Group by chapter (sorted by Chinese number)
  const chapterGroups = useMemo(() => {
    const map = new Map<string, Question[]>()
    for (const q of questions) {
      if (!map.has(q.chapter)) map.set(q.chapter, [])
      map.get(q.chapter)!.push(q)
    }
    return sortChapterEntries([...map.entries()])
  }, [questions.length])

  useEffect(() => {
    // Legacy sync: load from old localStorage and merge into store on first mount
    const stored = loadCards()
    if (store.cards.length === 0 && stored.length > 0) {
      store.setCards(stored)
    }
    const legacyUserQs = loadUserQuestions()
    if (store.userQuestions.length === 0 && legacyUserQs.length > 0) {
      store.setUserQuestions(legacyUserQs)
    }
    // Use store.cards for the initialization logic
    const currentCards = store.cards.length > 0 ? store.cards : stored
    const existingIds = new Set(currentCards.map((c: ReviewCard) => c.questionId))
    let changed = false
    const merged = [...currentCards]
    for (const q of questions) {
      if (!existingIds.has(q.id)) {
        merged.push(createCard(q.id))
        changed = true
      }
    }
    if (changed) store.setCards(merged)
  }, [questions.length])

  // Sync with server on mount if logged in
  useEffect(() => {
    if (isAuthenticated()) {
      pullAllFromServer().then(() => {
        // After server pull, sync old localStorage into store
        const fresh = loadCards()
        if (fresh.length > 0) {
          store.setCards(fresh)
          saveCards(fresh) // keep legacy localStorage in sync during transition
        }
      }).catch(() => {})
    }
  }, [])

  const dueCards = store.cards.filter((c) => {
    const today = new Date().toISOString().split('T')[0]
    return c.nextReview <= today
  })

  // Compute stats from store using existing getStats helper
  const stats = getStats(store.cards)

  const startReview = () => setShowModeModal(true)
  const startReviewWithMode = (mode: string) => {
    setShowModeModal(false)
    navigate(`/review?mode=${mode}`)
  }
  const resumeSession = () => {
    if (savedSession) {
      navigate(`/review?mode=${savedSession.mode}`)
    }
  }
  const startCustomReview = () => {
    if (selectedIds.size > 0) {
      navigate(`/review?ids=${[...selectedIds].join(',')}`)
    }
  }

  const toggleChapter = (chapter: string) => {
    setExpandedChapters((prev) => {
      const next = new Set(prev)
      if (next.has(chapter)) next.delete(chapter)
      else next.add(chapter)
      return next
    })
  }

  const toggleQuestion = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const selectChapter = (chapter: string) => {
    const chQuestions = chapterGroups.find(([ch]) => ch === chapter)?.[1] || []
    setSelectedIds((prev) => {
      const next = new Set(prev)
      const allSelected = chQuestions.every((q) => next.has(q.id))
      for (const q of chQuestions) {
        if (allSelected) next.delete(q.id)
        else next.add(q.id)
      }
      return next
    })
  }

  // Due by chapter
  const dueByChapter = new Map<string, ReviewCard[]>()
  for (const card of dueCards) {
    const q = questions.find((q) => q.id === card.questionId)
    const ch = q?.chapter || '未知章节'
    if (!dueByChapter.has(ch)) dueByChapter.set(ch, [])
    dueByChapter.get(ch)!.push(card)
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Hero card */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-indigo-600 via-indigo-700 to-purple-700 p-6 text-white shadow-lg shadow-indigo-500/20">
        <div className="relative z-10">
          <h1 className="text-2xl font-bold mb-2">
            {dueCards.length > 0 ? `今天有 ${dueCards.length} 道题待复习` : '全部搞定！'}
          </h1>
          <p className="text-indigo-200 text-sm mb-4">
            {dueCards.length > 0 ? '保持节奏，每天进步一点点' : '没有待复习的错题'}
          </p>
          <div className="flex gap-2.5">
            {savedSession ? (
              <>
                <button
                  onClick={resumeSession}
                  className="inline-flex items-center gap-2 px-5 py-2.5 bg-amber-400 text-amber-900 rounded-xl font-semibold text-sm hover:bg-amber-300 transition-all shadow-md active:scale-[0.98]"
                >
                  <Play size={16} />
                  继续上次 ({savedSession.ratedIndices?.length || 0}/{savedSession.cards?.length || 0})
                </button>
                <button
                  onClick={startReview}
                  className="inline-flex items-center gap-2 px-5 py-2.5 bg-white/10 text-white rounded-xl font-semibold text-sm hover:bg-white/20 transition-all active:scale-[0.98]"
                >
                  新开一轮
                </button>
              </>
            ) : (
              <button
                onClick={startReview}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-white text-indigo-700 rounded-xl font-semibold text-sm hover:bg-indigo-50 transition-all shadow-md active:scale-[0.98]"
              >
                <Play size={16} />
                {dueCards.length > 0 ? '开始复习' : '开始练习'}
              </button>
            )}
            <button
              onClick={() => setShowPicker(!showPicker)}
              className={`inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm transition-all active:scale-[0.98] ${
                showPicker ? 'bg-white/20 text-white' : 'bg-white/10 text-white/80 hover:bg-white/20'
              }`}
            >
              <ListFilter size={16} />
              自选题目
            </button>
          </div>
        </div>
        <div className="absolute -right-4 -top-4 w-32 h-32 rounded-full bg-white/10" />
        <div className="absolute -right-2 -bottom-8 w-24 h-24 rounded-full bg-white/5" />
      </div>

      {/* Custom question picker */}
      {showPicker && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden animate-slide-up">
          <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
            <h2 className="font-semibold text-slate-800 text-sm">选择要复习的题目</h2>
            <button
              onClick={startCustomReview}
              disabled={selectedIds.size === 0}
              className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                selectedIds.size > 0
                  ? 'bg-indigo-600 text-white hover:bg-indigo-700 active:scale-[0.98]'
                  : 'bg-slate-100 text-slate-400 cursor-not-allowed'
              }`}
            >
              开始 ({selectedIds.size}题)
            </button>
          </div>
          <div className="divide-y divide-slate-50 max-h-80 overflow-y-auto">
            {chapterGroups.map(([chapter, qs]) => {
              const isExpanded = expandedChapters.has(chapter)
              const chSelected = qs.filter((q) => selectedIds.has(q.id)).length
              return (
                <div key={chapter}>
                  <button
                    onClick={() => toggleChapter(chapter)}
                    className="w-full px-5 py-3 flex items-center justify-between hover:bg-slate-50 transition-colors text-left"
                  >
                    <div className="flex items-center gap-2.5">
                      <button
                        onClick={(e) => { e.stopPropagation(); selectChapter(chapter) }}
                        className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${
                          chSelected === qs.length ? 'bg-indigo-500 border-indigo-500' :
                          chSelected > 0 ? 'border-indigo-300 bg-indigo-50' : 'border-slate-300'
                        }`}
                      >
                        {chSelected === qs.length && <Check size={12} className="text-white" />}
                      </button>
                      <div>
                        <p className="text-sm font-medium text-slate-700">{chapter}</p>
                        <p className="text-xs text-slate-400">{qs.length} 题 · 已选 {chSelected}</p>
                      </div>
                    </div>
                    <ChevronRight size={16} className={`text-slate-300 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                  </button>
                  {isExpanded && (
                    <div className="bg-slate-50/50 px-5 py-2 space-y-1">
                      {qs.map((q) => (
                        <label
                          key={q.id}
                          className="flex items-center gap-3 py-2 px-3 rounded-lg hover:bg-white cursor-pointer transition-colors"
                        >
                          <input
                            type="checkbox"
                            checked={selectedIds.has(q.id)}
                            onChange={() => toggleQuestion(q.id)}
                            className="w-4 h-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 accent-indigo-600"
                          />
                          <span className="text-sm text-slate-600">
                            {q.questionNumber}
                            <span className="text-xs text-slate-400 ml-1.5">{q.originalNumber}</span>
                          </span>
                        </label>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Favorites entry */}
      {store.cards.filter((c) => c.favorited).length > 0 && !showPicker && (
        <button
          onClick={() => navigate('/review?favorites=1')}
          className="w-full flex items-center gap-3 px-4 py-3 bg-amber-50 border border-amber-200 rounded-xl hover:bg-amber-100 transition-colors"
        >
          <Star size={18} className="fill-amber-400 text-amber-400" />
          <div className="text-left flex-1">
            <p className="text-sm font-medium text-amber-700">收藏夹</p>
            <p className="text-xs text-amber-500">{store.cards.filter((c) => c.favorited).length} 道收藏题目</p>
          </div>
          <ChevronRight size={16} className="text-amber-400" />
        </button>
      )}

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-3">
        <StatCard icon={<Calendar size={18} className="text-orange-500" />} label="待复习" value={stats.due} color="bg-orange-50 border-orange-200" />
        <StatCard icon={<TrendingUp size={18} className="text-green-500" />} label="已掌握" value={stats.total - stats.due} color="bg-green-50 border-green-200" />
        <StatCard icon={<Zap size={18} className="text-blue-500" />} label="题库总数" value={stats.total} color="bg-blue-50 border-blue-200" />
      </div>

      {/* Due by chapter */}
      {!showPicker && dueByChapter.size > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-100">
            <h2 className="font-semibold text-slate-800 text-sm">待复习章节分布</h2>
          </div>
          <div className="divide-y divide-slate-50">
            {sortChapterEntries([...dueByChapter.entries()]).map(([chapter, chCards]) => {
              const ids = chCards.map((c) => c.questionId).join(',')
              return (
                <button
                  key={chapter}
                  onClick={() => navigate(`/review?ids=${ids}`)}
                  className="w-full px-5 py-3 flex items-center justify-between hover:bg-indigo-50 transition-colors text-left"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-700 truncate">{chapter}</p>
                    <p className="text-xs text-slate-400 mt-0.5">{chCards.length} 道题待复习</p>
                  </div>
                  <ChevronRight size={16} className="text-slate-300 flex-shrink-0" />
                </button>
              )
            })}
          </div>
        </div>
      )}

      {dueCards.length === 0 && !showPicker && (
        <button
          onClick={startReview}
          className="w-full py-4 bg-white rounded-xl border-2 border-dashed border-slate-300 text-slate-500 font-medium text-sm hover:border-indigo-400 hover:text-indigo-600 transition-all hover:scale-[1.005] active:scale-[0.98]"
        >
          + 手动开始一轮复习（所有题目随机）
        </button>
      )}

      {/* Mode selection modal */}
      {showModeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={() => setShowModeModal(false)}>
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm animate-fade-in" />
          <div className="relative bg-white rounded-2xl shadow-2xl p-6 w-full max-w-sm animate-scale-in" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-bold text-slate-800 text-center mb-1">选择复习模式</h3>
            <p className="text-xs text-slate-400 text-center mb-5">选定后本轮不可切换</p>
            <div className="space-y-3 stagger-children">
              <button onClick={() => startReviewWithMode('relaxed')}
                className="w-full p-4 rounded-xl border-2 border-purple-200 bg-purple-50/50 hover:bg-purple-100 hover:scale-[1.02] transition-all duration-200 text-left group card-hover">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-purple-100 flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                    <Sparkles size={20} className="text-purple-500" />
                  </div>
                  <div>
                    <p className="font-semibold text-slate-800 text-sm">宽松模式</p>
                    <p className="text-xs text-slate-500">自由练习，随时看答案，不限时</p>
                  </div>
                  <ChevronRight size={16} className="text-slate-300 ml-auto group-hover:translate-x-1 transition-transform" />
                </div>
              </button>
              <button onClick={() => startReviewWithMode('normal')}
                className="w-full p-4 rounded-xl border-2 border-amber-200 bg-amber-50/50 hover:bg-amber-100 hover:scale-[1.02] transition-all duration-200 text-left group card-hover">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-amber-100 flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                    <Timer size={20} className="text-amber-500" />
                  </div>
                  <div>
                    <p className="font-semibold text-slate-800 text-sm">普通模式</p>
                    <p className="text-xs text-slate-500">单题计时5分钟，逐题评分</p>
                  </div>
                  <ChevronRight size={16} className="text-slate-300 ml-auto group-hover:translate-x-1 transition-transform" />
                </div>
              </button>
              <button onClick={() => { setShowModeModal(false); navigate('/strict') }}
                className="w-full p-4 rounded-xl border-2 border-red-200 bg-red-50/50 hover:bg-red-100 hover:scale-[1.02] transition-all duration-200 text-left group card-hover">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-red-100 flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                    <Target size={20} className="text-red-500" />
                  </div>
                  <div>
                    <p className="font-semibold text-slate-800 text-sm">严格模式</p>
                    <p className="text-xs text-slate-500">随机10道选择题，模拟考试</p>
                  </div>
                  <ChevronRight size={16} className="text-slate-300 ml-auto group-hover:translate-x-1 transition-transform" />
                </div>
              </button>
            </div>
            <button onClick={() => setShowModeModal(false)}
              className="w-full mt-4 py-2.5 text-sm text-slate-400 hover:text-slate-600 transition-colors">
              取消
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function StatCard({
  icon, label, value, color,
}: {
  icon: React.ReactNode; label: string; value: number; color: string
}) {
  return (
    <div className={`${color} rounded-xl border p-4 flex flex-col gap-1`}>
      <div className="flex items-center gap-1.5">
        {icon}
        <span className="text-xs text-slate-500">{label}</span>
      </div>
      <span className="text-2xl font-bold text-slate-800">{value}</span>
    </div>
  )
}
