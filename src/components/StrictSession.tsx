import { useState, useMemo, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Check, X, Target, Timer, ChevronLeft, ChevronRight } from 'lucide-react'
import questionsData from '../data/questions.json'
import type { Question, Choice } from '../types'
import { loadCards, saveCards, loadUserQuestions, loadLogs, saveLogs } from '../lib/storage'
import { reviewCard } from '../lib/sm2'
import { renderContent } from '../lib/markdown'


function parseChoices(question: Question): Choice[] | null {
  // First check for explicit `choices` field in the data
  const rawChoices = (question as any).choices as { label?: string; letter?: string; text: string }[] | undefined
  if (rawChoices && rawChoices.length >= 2) {
    return rawChoices.map((ch) => ({ letter: ch.label || ch.letter || '', text: ch.text }))
  }
  // Fall back to parsing from problem text
  const problem = question.problem
  const fullMatch = problem.match(/\(([A-D])\)\s*(.+?)(?=\s*\([A-D]\)|$)/gs)
  if (!fullMatch || fullMatch.length < 2) return null
  const choices: Choice[] = []
  for (const m of fullMatch) {
    const m2 = m.match(/^\(([A-D])\)\s*(.+)/s)
    if (m2) choices.push({ letter: m2[1], text: m2[2].trim() })
  }
  return choices.length >= 2 ? choices : null
}

function parseCorrectLetter(correctAnswer: string): string | null {
  const stripped = correctAnswer.replace(/\*\*/g, '').trim()
  const m = stripped.match(/^[\(（]?([A-D])[\)）]?/)
  return m ? m[1] : null
}

type Stage = 'setup' | 'exam' | 'result'

export default function StrictSession() {
  const navigate = useNavigate()
  const [stage, setStage] = useState<Stage>('setup')
  const [examQuestions, setExamQuestions] = useState<Question[]>([])
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [currentIndex, setCurrentIndex] = useState(0)
  const [startTime, setStartTime] = useState<number>(0)
  const [endTime, setEndTime] = useState<number>(0)
  const [submitted, setSubmitted] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [reviewMode, setReviewMode] = useState(false)
  const [reviewIndex, setReviewIndex] = useState(0)

  const questions: Question[] = [...questionsData, ...loadUserQuestions()]
  const mcQuestions = questions.filter((q) => /\(A\)/.test(q.problem))

  // Timer
  useEffect(() => {
    if (stage !== 'exam' || submitted) return
    const iv = setInterval(() => setElapsed(Math.floor((Date.now() - startTime) / 1000)), 1000)
    return () => clearInterval(iv)
  }, [stage, submitted, startTime])

  // Auto-submit on leave
  useEffect(() => {
    const handler = () => {
      if (stage === 'exam' && !submitted) {
        submitExam()
      }
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [stage, submitted, examQuestions, answers])

  const score = useMemo(() => {
    if (!submitted) return null
    let correct = 0
    for (const q of examQuestions) {
      const userAnswer = answers[q.id]
      const correctLetter = parseCorrectLetter(q.correctAnswer)
      if (userAnswer && correctLetter && userAnswer === correctLetter) correct++
    }
    return { correct, total: examQuestions.length }
  }, [submitted, examQuestions, answers])

  const totalSeconds = submitted ? Math.floor((endTime - startTime) / 1000) : elapsed
  const formatTime = (sec: number) => {
    const m = Math.floor(sec / 60)
    const s = sec % 60
    return `${m}:${String(s).padStart(2, '0')}`
  }

  const startExam = (qs: Question[]) => {
    setExamQuestions(qs)
    setAnswers({})
    setCurrentIndex(0)
    setStartTime(Date.now())
    setElapsed(0)
    setSubmitted(false)
    setStage('exam')
  }

  const startFromExisting = () => {
    startExam(mcQuestions.slice(0, 10))
  }


  const selectAnswer = (questionId: string, letter: string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: letter }))
  }

  const submitExam = () => {
    const now = Date.now()
    setEndTime(now)
    setSubmitted(true)
    setStage('result')

    const cards = loadCards()
    const today = new Date().toISOString().split('T')[0]
    const newLogs: any[] = []
    for (const q of examQuestions) {
      const card = cards.find((c) => c.questionId === q.id)
      const correctLetter = parseCorrectLetter(q.correctAnswer)
      const isCorrect = answers[q.id] === correctLetter
      if (card) {
        const updated = reviewCard(card, isCorrect ? 'good' : 'again', isCorrect)
        const idx = cards.findIndex((c) => c.questionId === q.id)
        if (idx >= 0) cards[idx] = updated
      }
      newLogs.push({
        questionId: q.id,
        rating: isCorrect ? 'good' : 'again',
        date: today,
        mode: 'strict' as const,
        choiceSelected: answers[q.id] || null,
        choiceCorrect: isCorrect,
        timeSpent: Math.round((now - startTime) / examQuestions.length / 1000),
      })
    }
    saveCards(cards)
    const existingLogs = loadLogs()
    saveLogs([...existingLogs, ...newLogs])
  }

  const answeredCount = Object.keys(answers).length
  const currentQuestion = examQuestions[currentIndex]
  const choices = currentQuestion ? parseChoices(currentQuestion) : null
  const problemClean = currentQuestion
    ? currentQuestion.problem.replace(/\(([A-D])\)\s*.+?(?=\s*\([A-D]\)|$)/gs, '').replace(/^>\s*/gm, '').trim()
    : ''

  // Setup stage
  if (stage === 'setup') {
    return (
      <div className="space-y-5 animate-fade-in">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/')} className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-all">
            <ArrowLeft size={18} />
          </button>
          <h1 className="text-lg font-bold text-slate-800">严格模式</h1>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-red-50 to-red-100 flex items-center justify-center">
            <Target size={28} className="text-red-500" />
          </div>
          <h2 className="text-lg font-bold text-slate-800 mb-2">模拟考试</h2>
          <p className="text-sm text-slate-500 mb-1">随机抽取 10 道选择题</p>
          <p className="text-xs text-slate-400 mb-6">逐题作答，全部完成后交卷。离开页面自动交卷。</p>

          <div className="space-y-3">
            <button onClick={startFromExisting}
              className="w-full py-3 bg-gradient-to-r from-indigo-600 to-indigo-700 text-white rounded-xl font-semibold text-sm hover:from-indigo-700 hover:to-indigo-800 transition-all active:scale-[0.98] shadow-lg shadow-indigo-500/20">
              从题库随机抽 10 题
            </button>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
          <h3 className="font-semibold text-sm text-slate-800 mb-3">考试规则</h3>
          <ul className="space-y-2 text-sm text-slate-600">
            <li>1. 10道选择题，逐题作答</li>
            <li>2. 限时完成，全程计时</li>
            <li>3. 离开页面自动交卷</li>
            <li>4. 交卷后显示分数和正确答案</li>
          </ul>
        </div>
      </div>
    )
  }

  // Exam stage
  if (stage === 'exam' && currentQuestion) {
    return (
      <div className="space-y-4 animate-fade-in">
        {/* Top bar */}
        <div className="flex items-center gap-3">
          <button onClick={() => { if (confirm('退出将自动交卷，确定？')) submitExam() }}
            className="p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 transition-all" title="退出并交卷">
            <ArrowLeft size={18} />
          </button>
          <div className="flex-1 flex items-center gap-2">
            <span className="text-sm font-medium text-slate-700">{currentIndex + 1} / {examQuestions.length}</span>
            <div className="flex-1 h-1.5 bg-slate-200 rounded-full overflow-hidden">
              <div className="h-full bg-indigo-500 rounded-full transition-all" style={{ width: `${(answeredCount / examQuestions.length) * 100}%` }} />
            </div>
          </div>
          <span className="text-xs font-mono text-slate-500 flex items-center gap-1">
            <Timer size={14} />{formatTime(totalSeconds)}
          </span>
        </div>

        {/* Question card */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-6 py-3 border-b border-slate-100 bg-slate-50/50 flex items-center gap-2">
            <span className="text-xs font-bold text-indigo-500">第 {currentIndex + 1} 题</span>
            {currentQuestion.knowledgePoints?.slice(0, 2).map((kp) => (
              <span key={kp} className="text-[10px] px-1.5 py-0.5 rounded-full bg-indigo-50 text-indigo-500">{kp}</span>
            ))}
          </div>
          <div className="px-6 py-5">
            <div className="text-[15px] text-slate-700 leading-loose markdown-body"
              dangerouslySetInnerHTML={{ __html: renderContent(problemClean) }} />
            {choices && (
              <div className="mt-4 space-y-2">
                {choices.map((ch) => {
                  const selected = answers[currentQuestion.id] === ch.letter
                  return (
                    <button key={ch.letter} onClick={() => selectAnswer(currentQuestion.id, ch.letter)}
                      className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl border-2 text-left transition-all ${
                        selected
                          ? 'border-indigo-400 bg-indigo-50 text-indigo-700 ring-1 ring-indigo-400'
                          : 'border-slate-200 hover:border-indigo-200 hover:bg-slate-50'
                      }`}>
                      <span className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                        selected ? 'bg-indigo-500 text-white' : 'bg-slate-100 text-slate-500'
                      }`}>{ch.letter}</span>
                      <span className="text-sm" dangerouslySetInnerHTML={{ __html: renderContent(ch.text) }} />
                    </button>
                  )
                })}
              </div>
            )}
          </div>
        </div>

        {/* Navigation */}
        <div className="flex items-center gap-3">
          <button onClick={() => setCurrentIndex((i) => Math.max(0, i - 1))} disabled={currentIndex === 0}
            className="flex-1 py-2.5 rounded-xl font-semibold text-sm border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 transition-all disabled:opacity-30">
            上一题
          </button>
          <button onClick={() => {
            if (currentIndex < examQuestions.length - 1) setCurrentIndex((i) => i + 1)
          }} disabled={currentIndex >= examQuestions.length - 1}
            className="flex-1 py-2.5 rounded-xl font-semibold text-sm border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 transition-all disabled:opacity-30">
            下一题
          </button>
        </div>

        {/* Submit */}
        <button onClick={submitExam} disabled={answeredCount < examQuestions.length}
          className="w-full py-3.5 bg-red-600 text-white rounded-xl font-semibold text-sm hover:bg-red-700 transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-lg shadow-red-500/20">
          交卷 ({answeredCount}/{examQuestions.length})
        </button>
      </div>
    )
  }

  // Result stage - overview
  if (stage === 'result' && score && !reviewMode) {
    const wrongCount = score.total - score.correct
    const pct = Math.round((score.correct / score.total) * 100)
    const emoji = pct >= 80 ? '🎉' : pct >= 60 ? '📚' : '💪'

    const favoriteAllWrong = () => {
      if (wrongCount === 0) return
      const cards = loadCards()
      const wrongIds = new Set(
        examQuestions
          .filter((q) => answers[q.id] !== parseCorrectLetter(q.correctAnswer))
          .map((q) => q.id)
      )
      const updated = cards.map((c) =>
        wrongIds.has(c.questionId) ? { ...c, favorited: true } : c
      )
      saveCards(updated)
    }

    return (
      <div className="space-y-5 animate-fade-in">
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-8 text-center">
          <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <span className="text-3xl">{emoji}</span>
          </div>
          <h2 className="text-xl font-bold text-slate-800 mb-1">考试结束</h2>
          <p className="text-slate-500 text-sm mb-4">用时 {formatTime(totalSeconds)}</p>
          <div className="text-6xl font-bold text-indigo-600 mb-2">{pct}<span className="text-2xl text-indigo-400">分</span></div>
          <p className="text-sm text-slate-400">{score.correct} / {score.total} 正确</p>
        </div>

        <div className="space-y-3">
          <button onClick={() => { setReviewMode(true); setReviewIndex(0) }}
            className="w-full py-3.5 bg-indigo-600 text-white rounded-xl font-semibold text-sm hover:bg-indigo-700 transition-all active:scale-[0.98] shadow-lg shadow-indigo-500/20">
            查看解析
          </button>
          {wrongCount > 0 && (
            <button onClick={favoriteAllWrong}
              className="w-full py-3.5 bg-orange-500 text-white rounded-xl font-semibold text-sm hover:bg-orange-600 transition-all active:scale-[0.98] shadow-lg shadow-orange-500/20">
              收藏错题（{wrongCount}题）
            </button>
          )}
          <button onClick={() => navigate('/')}
            className="w-full py-3.5 bg-white text-slate-700 rounded-xl font-semibold text-sm border border-slate-200 hover:bg-slate-50 transition-all active:scale-[0.98]">
            返回首页
          </button>
        </div>
      </div>
    )
  }

  // Result stage - review mode (single question with navigation)
  if (stage === 'result' && score && reviewMode) {
    const q = examQuestions[reviewIndex]
    if (!q) return null
    const correctLetter = parseCorrectLetter(q.correctAnswer)
    const userAnswer = answers[q.id]
    const isCorrect = userAnswer === correctLetter
    const choices = parseChoices(q)
    const problemClean = q.problem.replace(/\(([A-D])\)\\s*.+?(?=\\s*\([A-D]\)|$)/gs, '').replace(/^>\\s*/gm, '').trim()

    return (
      <div className="space-y-4 animate-fade-in">
        {/* Top bar with progress */}
        <div className="flex items-center gap-3">
          <button onClick={() => setReviewMode(false)}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-all">
            <ArrowLeft size={18} />
          </button>
          <div className="flex-1 flex items-center gap-2">
            <span className="text-sm font-medium text-slate-700">{reviewIndex + 1} / {examQuestions.length}</span>
            <div className="flex-1 h-1.5 bg-slate-200 rounded-full overflow-hidden">
              <div className="h-full bg-indigo-500 rounded-full transition-all"
                style={{ width: `${((reviewIndex + 1) / examQuestions.length) * 100}%` }} />
            </div>
          </div>
        </div>

        {/* Question card with highlighted answers */}
        <div className={`bg-white rounded-2xl border shadow-sm overflow-hidden ${isCorrect ? 'border-green-200' : 'border-red-200'}`}>
          <div className={`px-5 py-2.5 border-b flex items-center gap-2 ${isCorrect ? 'bg-green-50/50 border-green-100' : 'bg-red-50/50 border-red-100'}`}>
            {isCorrect ? <Check size={15} className="text-green-500" /> : <X size={15} className="text-red-500" />}
            <span className="text-xs font-semibold">第 {reviewIndex + 1} 题</span>
            <span className={`text-xs ml-auto ${isCorrect ? 'text-green-600' : 'text-red-500'}`}>
              {isCorrect ? '正确' : `错误，正确答案 ${correctLetter}`}
            </span>
          </div>
          <div className="px-5 py-3">
            <div className="text-sm text-slate-700 leading-relaxed markdown-body"
              dangerouslySetInnerHTML={{ __html: renderContent(problemClean) }} />
            {choices && (
              <div className="mt-2 space-y-1">
                {choices.map((ch) => {
                  let style = 'border-slate-100 bg-slate-50 text-slate-500'
                  if (ch.letter === correctLetter) style = 'border-green-300 bg-green-50 text-green-700'
                  else if (ch.letter === userAnswer && !isCorrect) style = 'border-red-300 bg-red-50 text-red-700'
                  return (
                    <div key={ch.letter} className={`px-3 py-1.5 rounded-lg border text-sm flex items-center gap-2 ${style}`}>
                      <span className="text-xs font-bold">{ch.letter}.</span>
                      <span dangerouslySetInnerHTML={{ __html: renderContent(ch.text) }} />
                      {ch.letter === correctLetter && <Check size={14} className="text-green-500 ml-auto" />}
                      {ch.letter === userAnswer && !isCorrect && <X size={14} className="text-red-400 ml-auto" />}
                    </div>
                  )
                })}
              </div>
            )}
            {!isCorrect && q.correctAnswer && (
              <div className="mt-3 p-3 bg-green-50 rounded-lg border border-green-200 text-sm">
                <span className="text-xs font-semibold text-green-700">解答：</span>
                <div className="mt-1 text-slate-700" dangerouslySetInnerHTML={{ __html: renderContent(q.correctAnswer) }} />
                {q.steps && <div className="mt-2 text-slate-600" dangerouslySetInnerHTML={{ __html: renderContent(q.steps) }} />}
              </div>
            )}
          </div>
        </div>

        {/* Navigation */}
        <div className="flex items-center gap-3">
          <button onClick={() => setReviewIndex((i) => Math.max(0, i - 1))} disabled={reviewIndex === 0}
            className="flex-1 py-3 rounded-xl font-semibold text-sm border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 transition-all disabled:opacity-40 flex items-center justify-center gap-1.5">
            <ChevronLeft size={16} />上一题
          </button>
          <button onClick={() => setReviewIndex((i) => Math.min(examQuestions.length - 1, i + 1))} disabled={reviewIndex >= examQuestions.length - 1}
            className="flex-1 py-3 rounded-xl font-semibold text-sm border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 transition-all disabled:opacity-40 flex items-center justify-center gap-1.5">
            下一题<ChevronRight size={16} />
          </button>
        </div>

        {/* Back to results */}
        <button onClick={() => setReviewMode(false)}
          className="w-full py-3 bg-white text-slate-700 rounded-xl font-semibold text-sm border border-slate-200 hover:bg-slate-50 transition-all active:scale-[0.98]">
          返回结果
        </button>
      </div>
    )
  }

  return null
}


