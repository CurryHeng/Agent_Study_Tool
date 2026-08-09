import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, X, Plus } from 'lucide-react'
import questionsData from '../data/questions.json'
import type { Question, Workbook } from '../types'
import { addUserQuestion, addUserQuestionRemote, loadUserQuestions, loadCards, saveCards, sortChapters, getNextQuestionNumber, loadWorkbooks, DEFAULT_WORKBOOK_ID, migrateUserQuestions } from '../lib/storage'
import { createCard } from '../lib/sm2'

const DRAFT_KEY = 'quiz-app-draft-question'

export default function AddQuestion() {
  const navigate = useNavigate()

  // Form fields
  const [chapter, setChapter] = useState('')
  const [newChapter, setNewChapter] = useState('')
  const [questionNumber, setQuestionNumber] = useState('')
  const [originalNumber, setOriginalNumber] = useState('')
  const [problem, setProblem] = useState('')
  const [knowledgePoints, setKnowledgePoints] = useState<string[]>([])
  const [kpInput, setKpInput] = useState('')
  const [wrongAnswer, setWrongAnswer] = useState('')
  const [wrongReason, setWrongReason] = useState('')
  const [correctAnswer, setCorrectAnswer] = useState('')
  const [steps, setSteps] = useState('')
  const [summary, setSummary] = useState('')
  const [workbookId, setWorkbookId] = useState(DEFAULT_WORKBOOK_ID)
  const [workbooks] = useState<Workbook[]>(() => loadWorkbooks())
  const [submitted, setSubmitted] = useState(false)
  const manualNumber = useRef(false)
  const [hasDraft, setHasDraft] = useState(false)

  // ── Draft: load on mount ──
  useEffect(() => {
    try {
      const draft = localStorage.getItem(DRAFT_KEY)
      if (draft) setHasDraft(true)
    } catch { /* ignore */ }
  }, [])

  // ── Draft: auto-save form fields ──
  useEffect(() => {
    if (submitted) return
    const fields = {
      chapter, newChapter, questionNumber, originalNumber, problem,
      knowledgePoints, wrongAnswer, wrongReason, correctAnswer, steps, summary,
      workbookId,
    }
    const hasContent = problem.trim() || correctAnswer.trim() || chapter
    try {
      if (hasContent) {
        localStorage.setItem(DRAFT_KEY, JSON.stringify(fields))
      }
    } catch { /* ignore */ }
  }, [chapter, newChapter, questionNumber, originalNumber, problem, knowledgePoints, wrongAnswer, wrongReason, correctAnswer, steps, summary, workbookId, submitted])

  // ── Draft: warn before leaving ──
  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (problem.trim() || correctAnswer.trim()) {
        e.preventDefault()
      }
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [problem, correctAnswer])

  const restoreDraft = () => {
    try {
      const raw = localStorage.getItem(DRAFT_KEY)
      if (!raw) return
      const d = JSON.parse(raw)
      if (d.chapter) setChapter(d.chapter)
      if (d.newChapter) setNewChapter(d.newChapter)
      if (d.questionNumber) setQuestionNumber(d.questionNumber)
      if (d.originalNumber) setOriginalNumber(d.originalNumber)
      if (d.problem) setProblem(d.problem)
      if (d.knowledgePoints) setKnowledgePoints(d.knowledgePoints)
      if (d.wrongAnswer) setWrongAnswer(d.wrongAnswer)
      if (d.wrongReason) setWrongReason(d.wrongReason)
      if (d.correctAnswer) setCorrectAnswer(d.correctAnswer)
      if (d.steps) setSteps(d.steps)
      if (d.summary) setSummary(d.summary)
      if (d.workbookId) setWorkbookId(d.workbookId)
      setHasDraft(false)
    } catch { /* ignore */ }
  }

  const discardDraft = () => {
    localStorage.removeItem(DRAFT_KEY)
    setHasDraft(false)
  }

  // Migrate old data on mount
  useEffect(() => { migrateUserQuestions() }, [])

  // Auto-number: when chapter changes, compute next question number
  useEffect(() => {
    if (manualNumber.current) return
    const finalChapter = chapter === '__new__' ? newChapter.trim() : chapter
    if (!finalChapter) return
    const next = getNextQuestionNumber(finalChapter, allQuestions)
    if (next) setQuestionNumber(next)
  }, [chapter, newChapter])

  // Gather existing chapters
  const allQuestions: Question[] = [...questionsData, ...loadUserQuestions()]
  const existingChapters = sortChapters([...new Set(allQuestions.map((q) => q.chapter))])

  const addKnowledgePoint = () => {
    const kp = kpInput.trim()
    if (kp && !knowledgePoints.includes(kp)) {
      setKnowledgePoints([...knowledgePoints, kp])
    }
    setKpInput('')
  }

  const removeKnowledgePoint = (kp: string) => {
    setKnowledgePoints(knowledgePoints.filter((k) => k !== kp))
  }

  const handleKpKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      addKnowledgePoint()
    }
  }

  const handleSubmit = () => {
    const finalChapter = chapter === '__new__' ? newChapter.trim() : chapter.trim()
    if (!problem.trim()) { alert('请填写原题内容'); return }
    if (!correctAnswer.trim()) { alert('请填写正确答案'); return }
    if (!finalChapter) { alert('请选择或输入所属章节'); return }

    const num = questionNumber.trim() || '?'
    const id = 'user-' + Date.now()

    const question: Question = {
      id,
      chapter: finalChapter,
      questionNumber: num,
      originalNumber: originalNumber.trim() || '-',
      problem: problem.trim(),
      wrongAnswer: wrongAnswer.trim() || '（无）',
      wrongReason: wrongReason.trim() || '（未记录）',
      correctAnswer: correctAnswer.trim(),
      steps: steps.trim(),
      summary: summary.trim() || '（无总结）',
      knowledgePoints,
      workbookId,
    }
    addUserQuestion(question)
    addUserQuestionRemote(question)

    const cards = loadCards()
    cards.push(createCard(id))
    saveCards(cards)
    localStorage.removeItem(DRAFT_KEY)
    setSubmitted(true)
    setTimeout(() => navigate('/questions'), 800)
  }

  if (submitted) {
    return (
      <div className="flex items-center justify-center py-20 animate-fade-in">
        <div className="text-center">
          <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p className="text-lg font-semibold text-slate-800">错题已加入题库</p>
          <p className="text-sm text-slate-400 mt-1">即将返回题库...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-fade-in max-w-2xl">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button onClick={() => navigate('/questions')}
          className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors">
          <ArrowLeft size={20} />
        </button>
        <div>
          <h2 className="text-lg font-bold text-slate-800">加入错题</h2>
          <p className="text-xs text-slate-400">手动输入题目信息</p>
        </div>
      </div>

      {hasDraft && (
        <div className="px-4 py-3 bg-amber-50 border border-amber-200 rounded-xl text-sm flex items-center justify-between gap-3 animate-slide-up">
          <span className="text-amber-700">检测到未完成的草稿，是否恢复？</span>
          <div className="flex items-center gap-2 flex-shrink-0">
            <button onClick={restoreDraft}
              className="px-3 py-1 text-xs font-medium text-white bg-amber-600 rounded-lg hover:bg-amber-700 transition-colors">
              恢复
            </button>
            <button onClick={discardDraft}
              className="px-3 py-1 text-xs font-medium text-amber-600 bg-white border border-amber-300 rounded-lg hover:bg-amber-50 transition-colors">
              放弃
            </button>
          </div>
        </div>
      )}

      {/* Basic info */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-5">
        <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
          <span className="w-6 h-6 rounded-full bg-indigo-100 text-indigo-600 text-xs flex items-center justify-center font-bold">1</span>
          基本信息
        </h3>

        <div>
          <label className="block text-xs font-semibold text-slate-500 mb-1.5">原题编号（在书上的题号）</label>
          <input type="text" value={originalNumber} onChange={(e) => setOriginalNumber(e.target.value)}
            placeholder="例如：23"
            className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400" />
        </div>

        {questionNumber && (
          <div className="flex items-center gap-2 px-3 py-2 bg-indigo-50 rounded-lg border border-indigo-200">
            <span className="text-xs text-indigo-500 font-medium">错题编号</span>
            <span className="text-sm font-bold text-indigo-700">{questionNumber}</span>
            <span className="text-[10px] text-indigo-400">（自动生成）</span>
          </div>
        )}

        <div>
          <label className="block text-xs font-semibold text-slate-500 mb-1.5">原题内容 *</label>
          <textarea value={problem} onChange={(e) => setProblem(e.target.value)}
            placeholder="输入题目内容，支持 Markdown 和 $LaTeX$ 公式..."
            rows={5}
            className="w-full px-3 py-2.5 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 resize-y" />
        </div>

        {/* Workbook + Chapter + knowledge points */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-500 mb-1.5">所属练习册</label>
            <select value={workbookId} onChange={(e) => setWorkbookId(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 bg-white">
              {workbooks.map((wb) => (
                <option key={wb.id} value={wb.id}>{wb.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-500 mb-1.5">所属章节 *</label>
            <select value={chapter} onChange={(e) => setChapter(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 bg-white">
              <option value="">选择章节...</option>
              {existingChapters.map((ch) => (
                <option key={ch} value={ch}>{ch}</option>
              ))}
              <option value="__new__">+ 新建章节</option>
            </select>
            {chapter === '__new__' && (
              <input type="text" value={newChapter} onChange={(e) => setNewChapter(e.target.value)}
                placeholder="输入新章节名称"
                className="w-full mt-2 px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400" />
            )}
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-500 mb-1.5">知识点标签</label>
            <div className="flex gap-1.5">
              <input type="text" value={kpInput} onChange={(e) => setKpInput(e.target.value)}
                onKeyDown={handleKpKeyDown} placeholder="输入后回车添加"
                className="flex-1 px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400" />
              <button onClick={addKnowledgePoint}
                className="px-2.5 py-2 text-sm bg-slate-100 text-slate-600 rounded-lg hover:bg-slate-200 transition-colors">
                <Plus size={15} />
              </button>
            </div>
            {knowledgePoints.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {knowledgePoints.map((kp) => (
                  <span key={kp} className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-indigo-50 text-indigo-600">
                    {kp}
                    <button onClick={() => removeKnowledgePoint(kp)} className="hover:text-red-500 transition-colors"><X size={11} /></button>
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Wrong archive */}
        <div className="border-t border-slate-100 pt-5">
          <h3 className="text-sm font-semibold text-red-600 mb-3 flex items-center gap-1.5">
            <span className="w-1.5 h-4 rounded-full bg-red-400" />错误档案
          </h3>
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-500 mb-1.5">错误答案</label>
              <textarea value={wrongAnswer} onChange={(e) => setWrongAnswer(e.target.value)}
                placeholder="你当时选的/写的错误答案..." rows={2}
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500/20 focus:border-red-400 resize-y" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 mb-1.5">错误原因</label>
              <textarea value={wrongReason} onChange={(e) => setWrongReason(e.target.value)}
                placeholder="为什么会错？" rows={2}
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500/20 focus:border-red-400 resize-y" />
            </div>
          </div>
        </div>

        {/* Correct answer */}
        <div className="border-t border-slate-100 pt-5">
          <h3 className="text-sm font-semibold text-green-600 mb-3 flex items-center gap-1.5">
            <span className="w-1.5 h-4 rounded-full bg-green-400" />正确解析
          </h3>
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-500 mb-1.5">正确答案 *</label>
              <textarea value={correctAnswer} onChange={(e) => setCorrectAnswer(e.target.value)}
                placeholder="正确答案，支持 $LaTeX$ 公式..." rows={3}
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500/20 focus:border-green-400 resize-y" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 mb-1.5">核心步骤</label>
              <textarea value={steps} onChange={(e) => setSteps(e.target.value)}
                placeholder="解题的核心步骤..." rows={4}
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500/20 focus:border-green-400 resize-y" />
            </div>
          </div>
        </div>

        {/* Summary */}
        <div className="border-t border-slate-100 pt-5">
          <label className="block text-xs font-semibold text-slate-500 mb-1.5">一句话总结</label>
          <input type="text" value={summary} onChange={(e) => setSummary(e.target.value)}
            placeholder="用一句话总结这道题的关键点..."
            className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-400" />
        </div>
      </div>

      {/* Submit */}
      <div className="flex items-center gap-3">
        <button onClick={handleSubmit}
          className="flex-1 py-2.5 text-sm font-semibold text-white bg-indigo-600 rounded-xl hover:bg-indigo-700 active:scale-[0.98] transition-all">
          提交到题库
        </button>
        <button onClick={() => navigate('/questions')}
          className="px-6 py-2.5 text-sm font-medium text-slate-500 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 active:scale-[0.98] transition-all">
          取消
        </button>
      </div>
    </div>
  )
}
