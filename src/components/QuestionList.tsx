import { useState, useMemo, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, ChevronRight, Play, Star, Plus, Trash2, Edit3, Lightbulb, FileDown } from 'lucide-react'
import questionsData from '../data/questions.json'
import type { Question, ReviewCard } from '../types'
import { loadCards, loadUserQuestions, sortChapterEntries, getWorkbookId, loadWorkbooks, deleteUserQuestion, deleteCard, isUserQuestion, addWorkbook, addUserQuestion, addUserQuestionRemote, deleteUserQuestionRemote, saveCards, getNextQuestionNumber } from '../lib/storage'
import { createCard } from '../lib/sm2'
import { useAppStore } from '../lib/store'
import { renderContent } from '../lib/markdown'
import { jsPDF } from 'jspdf'
import html2canvas from 'html2canvas'

type QuestionWithCard = Question & { card?: ReviewCard }

export default function QuestionList() {
  const navigate = useNavigate()
  const store = useAppStore()
  const [search, setSearch] = useState('')
  const [expandedChapter, setExpandedChapter] = useState<string | null>(null)
  const [showFavorites, setShowFavorites] = useState(false)
  const [isEditMode, setIsEditMode] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [selectedWorkbookId, setSelectedWorkbookId] = useState<string>('all')
  const [showNewWbInput, setShowNewWbInput] = useState(false)
  const [newWbName, setNewWbName] = useState('')

  useEffect(() => {
    // Legacy sync: load from old localStorage and merge into store on first mount
    const legacyCards = loadCards()
    const legacyWorkbooks = loadWorkbooks()
    const legacyUserQs = loadUserQuestions()
    if (store.cards.length === 0 && legacyCards.length > 0) store.setCards(legacyCards)
    if (store.workbooks.length <= 1 && legacyWorkbooks.length > 0) store.setWorkbooks(legacyWorkbooks)
    if (store.userQuestions.length === 0 && legacyUserQs.length > 0) store.setUserQuestions(legacyUserQs)
  }, [])

  const questions: QuestionWithCard[] = useMemo(() => {
    const all = [...questionsData, ...store.userQuestions] as QuestionWithCard[]
    const cardMap = new Map(store.cards.map((c) => [c.questionId, c]))
    for (const q of all) q.card = cardMap.get(q.id)
    return all
  }, [store.cards, store.userQuestions])

  const favoritesSet = new Set(store.cards.filter((c) => c.favorited).map((c) => c.questionId))

  const filtered = (() => {
    let qs = questions
    if (selectedWorkbookId !== 'all') {
      qs = qs.filter((q) => getWorkbookId(q) === selectedWorkbookId)
    }
    if (showFavorites) qs = qs.filter((q) => favoritesSet.has(q.id))
    if (search.trim()) {
      qs = qs.filter(
        (q) =>
          q.problem.includes(search) ||
          q.summary.includes(search) ||
          q.chapter.includes(search) ||
          q.wrongReason.includes(search) ||
          q.knowledgePoints?.some((kp) => kp.includes(search))
      )
    }
    return qs
  })()

  function groupByChapter(qs: QuestionWithCard[]): [string, QuestionWithCard[]][] {
    const map = new Map<string, QuestionWithCard[]>()
    for (const q of qs) {
      if (!map.has(q.chapter)) map.set(q.chapter, [])
      map.get(q.chapter)!.push(q)
    }
    return sortChapterEntries([...map.entries()])
  }

  const grouped = groupByChapter(filtered)

  // ── Workbook tab counts ──
  const wbCounts = useMemo(() => {
    const counts = new Map<string, number>()
    counts.set('all', questions.length)
    for (const q of questions) {
      const wId = getWorkbookId(q)
      counts.set(wId, (counts.get(wId) || 0) + 1)
    }
    return counts
  }, [questions])

  // ── Delete handlers ──
  const handleDeleteQuestion = (id: string) => {
    if (!window.confirm('确定删除这道题目？此操作不可撤销。')) return
    deleteUserQuestion(id)
    deleteCard(id)
    // Sync to store
    store.setCards(loadCards())
    store.setUserQuestions(loadUserQuestions())
    deleteUserQuestionRemote(id)
  }

  const handleBatchDelete = () => {
    if (selectedIds.size === 0) return
    if (!window.confirm(`确定删除选中的 ${selectedIds.size} 道题目？此操作不可撤销。`)) return
    for (const id of selectedIds) {
      deleteUserQuestion(id)
      deleteCard(id)
      deleteUserQuestionRemote(id)
    }
    setSelectedIds(new Set())
    // Sync to store
    store.setCards(loadCards())
    store.setUserQuestions(loadUserQuestions())
  }

  const handleCreateVariant = (q: QuestionWithCard) => {
    const all = [...questionsData, ...store.userQuestions]
    const nextNum = getNextQuestionNumber(q.chapter, all)
    const variant: Question = {
      id: 'user-' + Date.now(),
      chapter: q.chapter,
      questionNumber: nextNum || '?',
      originalNumber: `原${q.questionNumber}举一反三`,
      problem: '',
      wrongAnswer: '（举一反三）',
      wrongReason: '（举一反三变体题）',
      correctAnswer: '',
      steps: '',
      summary: '',
      knowledgePoints: q.knowledgePoints || [],
      workbookId: getWorkbookId(q),
    }
    addUserQuestion(variant)
    addUserQuestionRemote(variant)
    const cards = loadCards()
    cards.push(createCard(variant.id))
    saveCards(cards)
    // Sync to store
    store.setCards(loadCards())
    store.setUserQuestions(loadUserQuestions())
    alert(`已创建举一反三题目 ${nextNum || '?'}，请在题库中补充题目内容和正确答案。`)
  }

  const selectChapterQuestions = (chapter: string) => {
    const chQs = grouped.find(([ch]) => ch === chapter)?.[1] || []
    const deletable = chQs.filter((q) => isUserQuestion(q.id))
    setSelectedIds((prev) => {
      const next = new Set(prev)
      const allSelected = deletable.every((q) => next.has(q.id))
      for (const q of deletable) {
        if (allSelected) next.delete(q.id)
        else next.add(q.id)
      }
      return next
    })
  }

  const toggleEditMode = () => {
    setIsEditMode(!isEditMode)
    setSelectedIds(new Set())
    setExpandedChapter(null)
    
  }

  const handleCreateWorkbook = () => {
    if (!newWbName.trim()) return
    addWorkbook(newWbName.trim())
    store.setWorkbooks(loadWorkbooks())
    setNewWbName('')
    setShowNewWbInput(false)
  }

  // ── PDF Export via jsPDF + html2canvas ──
  const exportPDF = async () => {
    const data = selectedWorkbookId === 'all' ? questions : questions.filter((q) => getWorkbookId(q) === selectedWorkbookId)
    const wbName = selectedWorkbookId === 'all' ? '全部题库' : (store.workbooks.find((w) => w.id === selectedWorkbookId)?.name || '题库')
    const groupedExport = groupByChapter(data)

    // Build export HTML with padding for margins
    let html = `<div style="font-family:sans-serif;padding:40px;max-width:760px;background:#fff;color:#1e293b">`
    html += `<h1 style="text-align:center;color:#4f46e5;margin-bottom:4px">题库导出</h1>`
    html += `<p style="text-align:center;color:#94a3b8;font-size:12px;margin-bottom:24px">${wbName} · ${data.length}题 · ${new Date().toLocaleDateString('zh-CN')}</p>`

    for (const [ch, qs] of groupedExport) {
      html += `<h2 style="color:#334155;border-bottom:2px solid #e2e8f0;padding-bottom:4px;margin-top:20px">${ch}（${qs.length}题）</h2>`
      for (const q of qs) {
        html += `<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:12px;margin-bottom:10px">`
        html += `<div style="margin-bottom:8px"><span style="background:#eef2ff;color:#4f46e5;padding:2px 8px;border-radius:4px;font-size:12px">${q.questionNumber}</span> <span style="color:#94a3b8;font-size:11px">${q.originalNumber}</span></div>`
        html += `<div style="font-size:14px;margin-bottom:8px">${renderContent(q.problem)}</div>`
        if (q.correctAnswer && q.correctAnswer !== '（见步骤）') {
          html += `<div style="font-size:11px;color:#64748b;margin-top:6px">正确答案：<span style="color:#16a34a;font-weight:500">${renderContent(q.correctAnswer)}</span></div>`
        }
        if (q.steps) {
          html += `<div style="font-size:12px;color:#475569;margin-top:4px">${renderContent(q.steps)}</div>`
        }
        html += `</div>`
      }
    }
    html += `</div>`

    // Hide container but keep it visible for html2canvas
    const container = document.createElement('div')
    container.style.position = 'fixed'
    container.style.left = '0'
    container.style.top = '0'
    container.style.width = '800px'
    container.style.zIndex = '-1'
    container.style.background = '#fff'
    container.innerHTML = html
    document.body.appendChild(container)

    // Load KaTeX CSS into the container for proper formula rendering
    const katexLink = document.createElement('link')
    katexLink.rel = 'stylesheet'
    katexLink.href = 'https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css'
    document.head.appendChild(katexLink)

    try {
      // Wait for KaTeX CSS to load and render
      await new Promise(r => setTimeout(r, 500))
      const canvas = await html2canvas(container, { scale: 3, useCORS: true, backgroundColor: '#ffffff', logging: false })
      const imgData = canvas.toDataURL('image/png')
      const pdf = new jsPDF('p', 'mm', 'a4')
      const pageWidth = pdf.internal.pageSize.getWidth()
      const pageHeight = pdf.internal.pageSize.getHeight()
      const imgWidth = pageWidth - 20
      const imgHeight = (canvas.height * imgWidth) / canvas.width
      let heightLeft = imgHeight
      let position = 10

      pdf.addImage(imgData, 'PNG', 10, position, imgWidth, imgHeight)
      heightLeft -= pageHeight - 20

      while (heightLeft > 0) {
        position = heightLeft - imgHeight + 10
        pdf.addPage()
        pdf.addImage(imgData, 'PNG', 10, position, imgWidth, imgHeight)
        heightLeft -= pageHeight - 20
      }

      pdf.save(`题库-${wbName}-${new Date().toISOString().split('T')[0]}.pdf`)
    } catch (e) {
      console.error('PDF export failed:', e)
      alert('导出失败，请重试')
    } finally {
      document.body.removeChild(container)
    }
  }

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Search */}
      <div className="relative">
        <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          value={search}
          onChange={(e) => {
            setSearch(e.target.value)
            setExpandedChapter(null)
            
          }}
          placeholder="搜索题目内容、知识点、错因..."
          className="w-full pl-10 pr-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 transition-all"
        />
      </div>

      {/* Workbook tabs */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
        <button
          onClick={() => { setSelectedWorkbookId('all'); setExpandedChapter(null) }}
          className={`text-xs px-3 py-1.5 rounded-full whitespace-nowrap transition-all flex-shrink-0 ${
            selectedWorkbookId === 'all'
              ? 'bg-indigo-600 text-white font-medium'
              : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
          }`}
        >
          全部 ({wbCounts.get('all') || 0})
        </button>
        {store.workbooks.map((wb) => {
          const count = wbCounts.get(wb.id) || 0
          return (
            <button key={wb.id}
              onClick={() => { setSelectedWorkbookId(wb.id); setExpandedChapter(null) }}
              className={`text-xs px-3 py-1.5 rounded-full whitespace-nowrap transition-all flex-shrink-0 ${
                selectedWorkbookId === wb.id
                  ? 'bg-indigo-600 text-white font-medium'
                  : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
              }`}
            >
              {wb.name} ({count})
            </button>
          )
        })}
        {showNewWbInput ? (
          <div className="flex items-center gap-1 flex-shrink-0">
            <input
              value={newWbName}
              onChange={(e) => setNewWbName(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleCreateWorkbook() }}
              placeholder="练习册名称"
              className="w-32 px-2 py-1 text-xs border border-indigo-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
              autoFocus
            />
            <button onClick={handleCreateWorkbook}
              className="text-[10px] px-2 py-1 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">确定</button>
            <button onClick={() => { setShowNewWbInput(false); setNewWbName('') }}
              className="text-[10px] px-2 py-1 text-slate-400 hover:text-slate-600">取消</button>
          </div>
        ) : (
          <button
            onClick={() => setShowNewWbInput(true)}
            className="text-xs px-2 py-1 rounded-full border border-dashed border-slate-300 text-slate-400 hover:border-indigo-400 hover:text-indigo-500 transition-all flex-shrink-0 flex items-center gap-0.5"
          >
            <Plus size={11} /> 题库
          </button>
        )}
      </div>

      {/* Actions row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <p className="text-xs text-slate-400">共 {filtered.length} 道题</p>
          <button
            onClick={() => setShowFavorites(!showFavorites)}
            className={`text-xs px-2 py-1 rounded-full transition-all ${
              showFavorites ? 'bg-amber-100 text-amber-700 font-medium' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
            }`}
          >
            <Star size={11} className="inline mr-0.5" />
            收藏 ({favoritesSet.size})
          </button>
          <button
            onClick={toggleEditMode}
            className={`text-xs px-2 py-1 rounded-full transition-all ${
              isEditMode ? 'bg-red-100 text-red-700 font-medium' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
            }`}
          >
            <Edit3 size={11} className="inline mr-0.5" />
            {isEditMode ? '取消' : '编辑'}
          </button>
        </div>
        <div className="flex items-center gap-2">
          {isEditMode && selectedIds.size > 0 && (
            <button
              onClick={handleBatchDelete}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-all active:scale-[0.98]"
            >
              <Trash2 size={13} /> 删除选中 ({selectedIds.size})
            </button>
          )}
          {!isEditMode && (
            <>
              <button
                onClick={() => navigate('/questions/add')}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-all active:scale-[0.98] border border-indigo-200"
              >
                <Plus size={13} /> 加入错题
              </button>
              <button
                onClick={exportPDF}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-emerald-600 bg-emerald-50 rounded-lg hover:bg-emerald-100 transition-all active:scale-[0.98] border border-emerald-200"
              >
                <FileDown size={13} /> 导出 PDF
              </button>
              <button
                onClick={() => navigate('/review')}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-all active:scale-[0.98]"
              >
                <Play size={13} /> 开始刷题
              </button>
            </>
          )}
        </div>
      </div>

      {/* Chapter list */}
      <div className="space-y-3">
        {grouped.map(([chapter, qs]) => {
          const deletableQs = qs.filter((q) => isUserQuestion(q.id))
          const chSelected = deletableQs.filter((q) => selectedIds.has(q.id)).length
          return (
            <div key={chapter} className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
              <button
                onClick={() => setExpandedChapter(expandedChapter === chapter ? null : chapter)}
                className="w-full px-5 py-3 flex items-center justify-between hover:bg-slate-50 transition-colors text-left"
              >
                <div className="flex items-center gap-2.5">
                  {isEditMode && deletableQs.length > 0 && (
                    <button
                      onClick={(e) => { e.stopPropagation(); selectChapterQuestions(chapter) }}
                      className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all flex-shrink-0 ${
                        chSelected === deletableQs.length ? 'bg-indigo-500 border-indigo-500' :
                        chSelected > 0 ? 'border-indigo-300 bg-indigo-50' : 'border-slate-300'
                      }`}
                    >
                      {chSelected === deletableQs.length && (
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                      )}
                    </button>
                  )}
                  <div>
                    <h3 className="text-sm font-semibold text-slate-800">{chapter}</h3>
                    <p className="text-xs text-slate-400 mt-0.5">{qs.length} 道题</p>
                  </div>
                </div>
                {!isEditMode && (
                  <ChevronRight
                    size={16}
                    className={`text-slate-300 transition-transform duration-200 ${expandedChapter === chapter ? 'rotate-90' : ''}`}
                  />
                )}
              </button>

              {expandedChapter === chapter && !isEditMode && (
                <div className="border-t border-slate-100 divide-y divide-slate-50 animate-slide-up">
                  {qs.map((q) => {
                    const fav = favoritesSet.has(q.id)
                    const card = q.card
                    const errorRate = card && card.totalAttempts > 0
                      ? Math.round((1 - card.totalCorrect / card.totalAttempts) * 100)
                      : null
                    const attempts = card?.totalAttempts || 0

                    return (
                      <div
                        key={q.id}
                        onClick={() => navigate(`/review?ids=${q.id}`)}
                        className="px-5 py-3 hover:bg-indigo-50/50 transition-colors cursor-pointer group flex items-start justify-between gap-3"
                      >
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1 flex-wrap">
                            <span className="text-xs font-medium text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded">
                              错题 {q.questionNumber}
                            </span>
                            <span className="text-[10px] text-slate-400">
                              {q.originalNumber.includes('举一反三') ? q.originalNumber : `原第${q.originalNumber}题`}
                            </span>
                            {fav && <Star size={11} className="fill-amber-400 text-amber-400" />}
                            {isUserQuestion(q.id) && (
                              <span className="text-[9px] px-1 py-0.5 rounded-full bg-amber-50 text-amber-600">自建</span>
                            )}
                            {errorRate !== null && (
                              <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
                                errorRate > 50 ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-600'
                              }`}>
                                错误率 {errorRate}%
                              </span>
                            )}
                            {attempts === 0 && (
                              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-400">未刷</span>
                            )}
                            {q.knowledgePoints?.slice(0, 2).map((kp) => (
                              <span key={kp} className="text-[9px] px-1.5 py-0.5 rounded-full bg-indigo-50 text-indigo-500">{kp}</span>
                            ))}
                          </div>
                          <div className="relative group/tip">
                            <span className="text-xs text-slate-400 cursor-help border-b border-dotted border-slate-300">查看原题</span>
                            <div className="absolute left-0 bottom-full mb-2 hidden group-hover/tip:block z-50 w-80 p-3 bg-white border border-slate-200 rounded-xl shadow-xl text-sm text-slate-700 leading-relaxed">
                              <div className="markdown-body" dangerouslySetInnerHTML={{ __html: renderContent(q.problem) }} />
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-1 flex-shrink-0" onClick={(e) => e.stopPropagation()}>
                          <button
                            onClick={() => handleCreateVariant(q)}
                            className="p-1 rounded text-slate-300 hover:text-amber-500 hover:bg-amber-50 transition-colors"
                            title={`举一反三（原${q.questionNumber}）`}
                          >
                            <Lightbulb size={13} />
                          </button>
                          {isUserQuestion(q.id) && (
                            <button
                              onClick={() => handleDeleteQuestion(q.id)}
                              className="p-1 rounded text-slate-300 hover:text-red-500 hover:bg-red-50 transition-colors"
                              title="删除此题"
                            >
                              <Trash2 size={13} />
                            </button>
                          )}
                          <Play size={14} className="text-slate-300 group-hover:text-indigo-500 transition-colors" />
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}

              {/* Edit mode: show checkboxes next to each question */}
              {expandedChapter === chapter && isEditMode && (
                <div className="border-t border-slate-100 divide-y divide-slate-50 animate-slide-up">
                  {qs.map((q) => {
                    const canDelete = isUserQuestion(q.id)
                    return (
                      <label
                        key={q.id}
                        className={`flex items-center gap-3 px-5 py-3 cursor-pointer transition-colors ${
                          canDelete && selectedIds.has(q.id) ? 'bg-red-50' : canDelete ? 'hover:bg-slate-50' : 'bg-slate-50/50'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={selectedIds.has(q.id)}
                          disabled={!canDelete}
                          onChange={() => {
                            if (!canDelete) return
                            setSelectedIds((prev) => {
                              const next = new Set(prev)
                              if (next.has(q.id)) next.delete(q.id)
                              else next.add(q.id)
                              return next
                            })
                          }}
                          className={`w-4 h-4 rounded border-slate-300 focus:ring-indigo-500 ${canDelete ? 'accent-indigo-600' : 'opacity-30'}`}
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-xs font-medium text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded">
                              错题 {q.questionNumber}
                            </span>
                            <span className="text-[10px] text-slate-400">
                              {q.originalNumber.includes('举一反三') ? q.originalNumber : `原第${q.originalNumber}题`}
                            </span>
                            {canDelete ? (
                              <span className="text-[9px] px-1 py-0.5 rounded-full bg-amber-50 text-amber-600">自建</span>
                            ) : (
                              <span className="text-[9px] px-1 py-0.5 rounded-full bg-slate-100 text-slate-400">内置</span>
                            )}
                          </div>
                          <div className="text-sm text-slate-700 line-clamp-1 mt-1">{q.problem.slice(0, 80)}</div>
                        </div>
                      </label>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}

        {grouped.length === 0 && (
          <div className="text-center py-12 text-slate-400">
            <p className="text-sm">没有找到匹配的题目</p>
          </div>
        )}
      </div>
    </div>
  )
}
