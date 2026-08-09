import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate, useSearchParams, useLocation } from 'react-router-dom'
import { ArrowLeft, CheckCircle, XCircle, ChevronLeft, ChevronRight, Check, AlertCircle } from 'lucide-react'
import questionsData from '../data/questions.json'
import type { Question, ReviewCard, Rating, QuizMode, WrongRecord } from '../types'
import { loadCards, saveCards, saveCardsRemote, loadLogs, saveLogs, saveLogsRemote, toggleFavorite, toggleFavoriteRemote, loadUserQuestions, getWorkbookId, loadWorkbooks, DEFAULT_WORKBOOK_ID } from '../lib/storage'
import { createCard, reviewCard } from '../lib/sm2'
import QuestionCard from './QuestionCard'
import RatingButtons from './RatingButtons'
// AI feature removed
import QuestionTimer from './QuestionTimer'
import { useAppStore } from '../lib/store'

const NORMAL_MODE_SECONDS = 300

const MODE_LABEL: Record<QuizMode, string> = {
  relaxed: '宽松模式',
  normal: '普通模式',
  strict: '严格模式',
}

export default function QuizSession() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const customIds = searchParams.get('ids')?.split(',').filter(Boolean)
  const favoritesOnly = searchParams.get('favorites') === '1'
  const modeParam = searchParams.get('mode') as QuizMode | null
  const mode: QuizMode = modeParam === 'normal' || modeParam === 'strict' ? modeParam : 'relaxed'

  const [cards, setCards] = useState<ReviewCard[]>([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [revealed, setRevealed] = useState(false)
  const [ratedIndices, setRatedIndices] = useState<Set<number>>(new Set())
  const [sessionDone, setSessionDone] = useState(false)
  const [sessionResults, setSessionResults] = useState<{ q: Question; rating: Rating; choiceCorrect?: boolean }[]>([])
  const [choiceResult, setChoiceResult] = useState<{ selected: string; correct: boolean } | null>(null)
  const [timedOut, setTimedOut] = useState(false)
  const [showWrongForm, setShowWrongForm] = useState(false)
  const [selfAssessed, setSelfAssessed] = useState<boolean | null>(null)
  const [wrongAnswerInput, setWrongAnswerInput] = useState('')
  const [wrongReasonInput, setWrongReasonInput] = useState('')
  const [timerKey, setTimerKey] = useState(0)
  const questionStartTime = useRef(Date.now())
  const store = useAppStore()

  // Session persistence key — always the same key, one saved session at a time
  const SESSION_KEY = 'quiz-session-last'

  const location = useLocation()
  const questions: Question[] = [...questionsData, ...store.userQuestions]
  const navKey = location.key

  useEffect(() => {
    // Try to restore the last saved session
    const saved = localStorage.getItem(SESSION_KEY)
    if (saved && !customIds && !favoritesOnly) {
      try {
        const parsed = JSON.parse(saved)
        if (parsed.mode === mode && parsed.cards?.length > 0) {
          setCards(parsed.cards)
          setCurrentIndex(parsed.currentIndex || 0)
          setRatedIndices(new Set(parsed.ratedIndices || []))
          setSessionResults(parsed.sessionResults || [])
          setRevealed(false)
          setChoiceResult(null)
          setTimedOut(false)
          setSessionDone(false)
          return // Restored, skip fresh start
        }
      } catch { /* ignore */ }
    }

    // No saved session — start fresh
    let stored = store.cards.length > 0 ? [...store.cards] : loadCards()
    if (store.cards.length === 0 && stored.length > 0) {
      store.setCards(stored)
    }
    // Legacy sync for userQuestions and workbooks
    if (store.userQuestions.length === 0) {
      const legacyUserQs = loadUserQuestions()
      if (legacyUserQs.length > 0) store.setUserQuestions(legacyUserQs)
    }
    if (store.workbooks.length <= 1) {
      const legacyWbs = loadWorkbooks()
      if (legacyWbs.length > 0) store.setWorkbooks(legacyWbs)
    }

    if (stored.length < questions.length) {
      const existingIds = new Set(stored.map((c) => c.questionId))
      let changed = false
      for (const q of questions) {
        if (!existingIds.has(q.id)) {
          stored.push(createCard(q.id))
          changed = true
        }
      }
      if (changed) {
        store.setCards(stored)
        saveCards(stored)
      }
    }

    if (customIds) {
      const idSet = new Set(customIds)
      stored = stored.filter((c) => idSet.has(c.questionId))
    }

    if (favoritesOnly) {
      stored = stored.filter((c) => c.favorited)
    }

    const today = new Date().toISOString().split('T')[0]
    const due = stored.filter((c) => c.nextReview <= today)
    const rest = stored.filter((c) => c.nextReview > today)
    const shuffle = <T,>(arr: T[]) => {
      for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1))
        ;[arr[i], arr[j]] = [arr[j], arr[i]]
      }
      return arr
    }
    setCards([...shuffle(due), ...shuffle(rest)])
    // Reset UI state for new session
    setCurrentIndex(0)
    setRevealed(false)
    setRatedIndices(new Set())
    setSessionDone(false)
    setSessionResults([])
    setChoiceResult(null)
    setTimedOut(false)
  }, [navKey, questions.length])

  // Save session state to localStorage on every state change
  useEffect(() => {
    if (cards.length > 0) {
      localStorage.setItem(SESSION_KEY, JSON.stringify({
        mode,
        cards,
        currentIndex,
        ratedIndices: [...ratedIndices],
        sessionResults,
      }))
    }
  }, [cards, currentIndex, ratedIndices, sessionResults, mode])

  // Clear saved session when explicitly done
  useEffect(() => {
    if (sessionDone) {
      localStorage.removeItem(SESSION_KEY)
    }
  }, [sessionDone])

  const currentCard = cards[currentIndex]
  const currentQuestion = currentCard ? questions.find((q) => q.id === currentCard.questionId) : null
  const progress = cards.length > 0 ? (ratedIndices.size / cards.length) * 100 : 0
  const allRated = ratedIndices.size >= cards.length

  // Auto-reveal when choices are answered
  const handleChoiceResult = useCallback((selected: string, correct: boolean) => {
    setChoiceResult({ selected, correct })
    setRevealed(true)
  }, [])

  const handleRate = useCallback(
    (rating: Rating) => {
      if (!currentCard || !currentQuestion) return

      const isCorrect = choiceResult ? choiceResult.correct : (selfAssessed ?? (rating === 'good' || rating === 'easy'))
      const updated = reviewCard(currentCard, rating, isCorrect)
      const newCards = cards.map((c) => (c.questionId === currentCard.questionId ? updated : c))
      setCards(newCards)
      // Write to both store and legacy localStorage
      store.updateCard(currentCard.questionId, updated)
      saveCards(newCards)
      // Sync single card update to server
      saveCardsRemote([updated])

      const logs = loadLogs()
      const timeSpent = Math.round((Date.now() - questionStartTime.current) / 1000)
      const newLog = {
        questionId: currentCard.questionId,
        rating,
        date: new Date().toISOString().split('T')[0],
        mode,
        timeSpent,
        ...(choiceResult ? { choiceSelected: choiceResult.selected, choiceCorrect: choiceResult.correct } : {}),
      }
      logs.push(newLog)
      saveLogs(logs)
      store.setLogs(logs)
      saveLogsRemote([newLog])

      setSessionResults((prev) => [...prev, { q: currentQuestion, rating, choiceCorrect: choiceResult?.correct }])
      setRatedIndices((prev) => new Set(prev).add(currentIndex))
      if (rating === 'again' || rating === 'hard') setShowWrongForm(true)
    },
    [currentCard, currentIndex, cards, currentQuestion, choiceResult, mode]
  )

  const saveWrongRecord = useCallback(() => {
    if (!currentCard) return
    const record: WrongRecord = {
      date: new Date().toISOString().split('T')[0],
      wrongAnswer: wrongAnswerInput.trim(),
      wrongReason: wrongReasonInput.trim(),
    }
    const newCards = cards.map((c) =>
      c.questionId === currentCard.questionId
        ? { ...c, wrongRecords: [...c.wrongRecords, record] }
        : c
    )
    setCards(newCards)
    // Write to both store and legacy localStorage
    store.addWrongRecord(currentCard.questionId, record)
    saveCards(newCards)
    const updatedCard = newCards.find((c) => c.questionId === currentCard.questionId)
    if (updatedCard) saveCardsRemote([updatedCard])
    setShowWrongForm(false)
    setWrongAnswerInput('')
    setWrongReasonInput('')
  }, [currentCard, cards, wrongAnswerInput, wrongReasonInput])

  const handleToggleFavorite = useCallback(() => {
    if (!currentCard) return
    // Use store toggleFavorite (also writes to legacy localStorage)
    store.toggleFavorite(currentCard.questionId)
    const newCards = toggleFavorite(cards, currentCard.questionId)
    setCards(newCards)
    saveCards(newCards)
    toggleFavoriteRemote(newCards, currentCard.questionId)
  }, [cards, currentCard, store])

  const handleTimeout = useCallback(() => {
    if (!revealed) {
      setRevealed(true)
      setTimedOut(true)
    }
  }, [revealed])

  const resetQuestion = () => {
    setRevealed(false)
    setChoiceResult(null)
    setTimedOut(false)
    setShowWrongForm(false)
    setSelfAssessed(null)
    setWrongAnswerInput('')
    setWrongReasonInput('')
    setTimerKey((k) => k + 1)
    questionStartTime.current = Date.now()
  }

  const goNext = () => {
    if (currentIndex < cards.length - 1) {
      setCurrentIndex(currentIndex + 1)
      resetQuestion()
    }
  }

  const goPrev = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1)
      resetQuestion()
    }
  }

  const finishSession = () => setSessionDone(true)

  const restartSession = () => {
    setCurrentIndex(0)
    setRevealed(false)
    setSessionDone(false)
    setSessionResults([])
    setChoiceResult(null)
    setTimedOut(false)
    setShowWrongForm(false)
    setSelfAssessed(null)
    setWrongAnswerInput('')
    setWrongReasonInput('')
    setRatedIndices(new Set())
    const shuffle = <T,>(arr: T[]) => {
      for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1))
        ;[arr[i], arr[j]] = [arr[j], arr[i]]
      }
      return arr
    }
    setCards(shuffle([...cards]))
  }

  // Session complete screen
  if (sessionDone) {
    const correct = sessionResults.filter((r) => r.rating === 'good' || r.rating === 'easy')
    const wrong = sessionResults.filter((r) => r.rating === 'again' || r.rating === 'hard')
    const rate = sessionResults.length > 0 ? Math.round((correct.length / sessionResults.length) * 100) : 0
    const choiceResults = sessionResults.filter((r) => r.choiceCorrect !== undefined)
    const choiceCorrect = choiceResults.filter((r) => r.choiceCorrect).length
    const choiceRate = choiceResults.length > 0 ? Math.round((choiceCorrect / choiceResults.length) * 100) : null

    return (
      <div className="space-y-5 animate-fade-in">
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow p-8 text-center">
          <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <span className="text-3xl">{rate >= 80 ? '🎉' : rate >= 50 ? '📚' : '💪'}</span>
          </div>
          <h2 className="text-xl font-bold text-slate-800 mb-2">本轮复习完成！</h2>
          <p className="text-slate-500 text-sm mb-6">共复习 {sessionResults.length} 道题，掌握率 {rate}%</p>

          <div className="w-24 h-24 mx-auto mb-6 relative">
            <svg viewBox="0 0 36 36" className="w-full h-full transform -rotate-90">
              <circle cx="18" cy="18" r="15.9" fill="none" stroke="#e2e8f0" strokeWidth="3" />
              <circle cx="18" cy="18" r="15.9" fill="none" stroke="url(#grad)" strokeWidth="3"
                strokeDasharray={`${rate} ${100 - rate}`} strokeLinecap="round" />
              <defs>
                <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#6366f1" />
                  <stop offset="100%" stopColor="#a855f7" />
                </linearGradient>
              </defs>
            </svg>
            <span className="absolute inset-0 flex items-center justify-center text-lg font-bold text-slate-700">{rate}%</span>
          </div>

          <div className="flex justify-center gap-4 text-sm">
            <div className="flex items-center gap-1.5">
              <CheckCircle size={16} className="text-green-500" />
              <span className="text-slate-600">掌握 {correct.length}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <XCircle size={16} className="text-red-400" />
              <span className="text-slate-600">需复习 {wrong.length}</span>
            </div>
          </div>

          {choiceRate !== null && (
            <div className="mt-4 pt-4 border-t border-slate-100">
              <p className="text-xs text-slate-400 mb-2">选择题正确率</p>
              <div className="flex items-center justify-center gap-2">
                <span className="text-lg font-bold text-slate-700">{choiceCorrect}</span>
                <span className="text-slate-300">/</span>
                <span className="text-lg font-bold text-slate-700">{choiceResults.length}</span>
                <span className="text-sm font-medium text-indigo-600 ml-1">({choiceRate}%)</span>
              </div>
            </div>
          )}
        </div>

        {wrong.length > 0 && (
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
            <h3 className="font-semibold text-sm text-slate-800 mb-3">需要复习的题目</h3>
            <div className="space-y-2">
              {wrong.map((r) => (
                <div key={r.q.id} className="text-sm text-slate-600 py-1.5 px-3 bg-red-50 rounded-lg">{r.q.chapter} · 错题 {r.q.questionNumber}</div>
              ))}
            </div>
          </div>
        )}

        <div className="flex gap-3">
          <button onClick={restartSession}
            className="flex-1 py-3 bg-indigo-600 text-white rounded-xl font-semibold text-sm hover:bg-indigo-700 transition-all active:scale-[0.98] hover:scale-[1.01] shadow-lg shadow-indigo-500/20">
            再来一轮
          </button>
          <button onClick={() => navigate('/')}
            className="flex-1 py-3 bg-white text-slate-700 rounded-xl font-semibold text-sm border border-slate-200 hover:bg-slate-50 transition-all active:scale-[0.98]">
            返回首页
          </button>
        </div>
      </div>
    )
  }

  if (!currentCard || !currentQuestion) {
    return (
      <div className="text-center py-16">
        <p className="text-slate-400">加载中...</p>
      </div>
    )
  }

  const isRated = ratedIndices.has(currentIndex)
  const isChoice = parseChoicesCheck(currentQuestion)

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Top bar */}
      <div className="flex items-center gap-3">
        <button onClick={() => navigate('/')}
          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-all hover:scale-105 active:scale-90">
          <ArrowLeft size={18} />
        </button>
        <div className="flex-1 h-2 bg-slate-200 rounded-full overflow-hidden progress-bar">
          <div className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all duration-700 ease-out"
            style={{ width: `${progress}%` }} />
        </div>
        <span className="text-xs font-medium text-slate-400 tabular-nums w-16 text-right">
          {ratedIndices.size}/{cards.length}
        </span>
      </div>

      {/* Chapter + mode + status badges */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-600 font-medium">
          {currentQuestion.chapter}
        </span>
        {(() => {
          const wbId = getWorkbookId(currentQuestion)
          const wb = store.workbooks.find((w) => w.id === wbId)
          if (wb && wb.id !== DEFAULT_WORKBOOK_ID) {
            return <span className="text-[10px] px-2 py-0.5 rounded-full bg-teal-50 text-teal-600 font-medium">{wb.name}</span>
          }
          return null
        })()}
        <span className="text-xs text-slate-400">
          错题 {currentQuestion.questionNumber}（原第 {currentQuestion.originalNumber} 题）
        </span>

        {/* Mode badge (fixed for session) */}
        <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ml-auto ${
          mode === 'strict' ? 'bg-red-50 text-red-600 border border-red-200' :
          mode === 'normal' ? 'bg-amber-50 text-amber-600 border border-amber-200' :
          'bg-purple-50 text-purple-600 border border-purple-200'
        }`}>
          {MODE_LABEL[mode]}
        </span>

        {customIds && (
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-50 text-purple-500 font-medium">自选 {cards.length} 题</span>
        )}
        {favoritesOnly && (
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-50 text-amber-600 font-medium">收藏夹</span>
        )}
        {isRated && (
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-500 font-medium">已评级</span>
        )}
      </div>

      {/* Question card */}
      <QuestionCard
        question={currentQuestion}
        revealed={revealed}
        onChoiceResult={handleChoiceResult}
        favorited={currentCard.favorited}
        onToggleFavorite={handleToggleFavorite}
        wrongRecords={currentCard.wrongRecords}
      />

      {/* Timer for normal mode */}
      {mode === 'normal' && !revealed && (
        <QuestionTimer key={timerKey} seconds={NORMAL_MODE_SECONDS} running={!revealed} onTimeout={handleTimeout} />
      )}
      {/* Count-up timer for time tracking */}
      {!revealed && (
        <QuestionTimer key={timerKey} seconds={0} running={!revealed} countUp className="text-xs text-slate-400" />
      )}
      {timedOut && (
        <div className="px-4 py-2.5 bg-red-50 border border-red-200 rounded-xl text-sm text-red-600 flex items-center gap-2 animate-slide-up">
          <AlertCircle size={15} /> 时间到！请查看答案并评分
        </div>
      )}

      {/* Actions */}
      {!revealed && !isChoice && (
        <button onClick={() => setRevealed(true)}
          className="w-full py-3.5 bg-indigo-600 text-white rounded-xl font-semibold text-sm hover:bg-indigo-700 hover:scale-[1.005] transition-all active:scale-[0.98] shadow-lg shadow-indigo-500/20">
          揭晓答案
        </button>
      )}

      {/* Rating & wrong-recording after reveal */}
      {revealed && (
        <>
          {/* Non-choice self-assessment: ask user if they got it right */}
          {!isChoice && selfAssessed === null && !isRated && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 animate-slide-up">
              <p className="text-xs text-slate-400 text-center mb-3">揭晓答案后，你觉得自己做对了吗？</p>
              <div className="flex gap-3">
                <button onClick={() => setSelfAssessed(true)}
                  className="flex-1 py-3 bg-emerald-500 text-white rounded-xl font-semibold text-sm hover:bg-emerald-600 transition-all active:scale-[0.98] shadow-sm">
                  我做对了
                </button>
                <button onClick={() => setSelfAssessed(false)}
                  className="flex-1 py-3 bg-red-500 text-white rounded-xl font-semibold text-sm hover:bg-red-600 transition-all active:scale-[0.98] shadow-sm">
                  我做错了
                </button>
              </div>
            </div>
          )}

          {!isRated && (isChoice || selfAssessed !== null) && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 animate-slide-up">
              <p className="text-xs text-slate-400 text-center mb-3">你对这道题的掌握程度如何？</p>
              <RatingButtons onRate={handleRate} card={currentCard} allowedRatings={
                isChoice
                  ? (choiceResult?.correct === true ? ['good', 'easy'] : choiceResult?.correct === false ? ['again', 'hard'] : undefined)
                  : (selfAssessed === true ? ['good', 'easy'] : selfAssessed === false ? ['again', 'hard'] : undefined)
              } />
            </div>
          )}
          {isRated && !showWrongForm && (
            <div className="flex items-center justify-center gap-2 py-3 px-4 bg-slate-50 rounded-xl border border-slate-200 animate-slide-up">
              <Check size={16} className="text-green-500" />
              <span className="text-sm text-slate-600 font-medium">已记录掌握程度</span>
            </div>
          )}

          {/* Wrong record form */}
          {showWrongForm && (
            <div className="bg-orange-50 rounded-xl border border-orange-200 p-5 space-y-4 animate-slide-up">
              <div className="flex items-center gap-2">
                <AlertCircle size={16} className="text-orange-500" />
                <span className="text-sm font-semibold text-orange-700">记录错因（可选，支持 Markdown）</span>
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">你的错误答案</label>
                <textarea value={wrongAnswerInput} onChange={(e) => setWrongAnswerInput(e.target.value)}
                  placeholder="写下你做错的答案或过程…" rows={3}
                  className="mt-1.5 w-full px-3 py-2 text-sm border border-orange-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-orange-500/20 focus:border-orange-400 resize-y" />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">错误原因分析</label>
                <textarea value={wrongReasonInput} onChange={(e) => setWrongReasonInput(e.target.value)}
                  placeholder="分析一下为什么会做错…" rows={2}
                  className="mt-1.5 w-full px-3 py-2 text-sm border border-orange-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-orange-500/20 focus:border-orange-400 resize-y" />
              </div>
              <div className="flex gap-2">
                <button onClick={saveWrongRecord}
                  className="flex-1 py-2.5 bg-orange-600 text-white rounded-xl font-semibold text-sm hover:bg-orange-700 transition-all active:scale-[0.98]">
                  保存到错误档案
                </button>
                <button onClick={() => setShowWrongForm(false)} className="px-4 py-2.5 text-sm text-slate-500 hover:text-slate-700 transition-colors">跳过</button>
              </div>
            </div>
          )}

{/* AI SimilarQuestion removed */}
        </>
      )}

      {/* Navigation */}
      <div className="flex items-center gap-3">
        <button onClick={goPrev} disabled={currentIndex === 0}
          className="flex-1 py-3 rounded-xl font-semibold text-sm border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 hover:scale-[1.01] transition-all active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-1.5">
          <ChevronLeft size={16} />上一题
        </button>
        <button onClick={goNext} disabled={currentIndex >= cards.length - 1}
          className="flex-1 py-3 rounded-xl font-semibold text-sm border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 hover:scale-[1.01] transition-all active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-1.5">
          下一题<ChevronRight size={16} />
        </button>
      </div>

      {/* Finish button */}
      {allRated && (
        <button onClick={finishSession}
          className="w-full py-3.5 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-xl font-semibold text-sm hover:from-indigo-700 hover:to-purple-700 hover:scale-[1.005] transition-all active:scale-[0.98] shadow-lg shadow-indigo-500/20">
          完成复习，查看结果
        </button>
      )}
    </div>
  )
}

function parseChoicesCheck(question: Question): boolean {
  if ((question as any).choices?.length >= 2) return true
  return /\(A\)/.test(question.problem)
}
