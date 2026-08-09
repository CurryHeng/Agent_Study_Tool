import { useEffect, useRef, useState, useMemo } from 'react'
import type { Question, Choice, WrongRecord } from '../types'
import { Lightbulb, AlertTriangle, CheckCircle2, BookOpen, X, Check, Star } from 'lucide-react'
import { renderContent } from '../lib/markdown'
import { useAppStore } from '../lib/store'

interface Props {
  question: Question
  revealed: boolean
  onChoiceResult?: (selected: string, correct: boolean) => void
  favorited?: boolean
  onToggleFavorite?: () => void
  wrongRecords?: WrongRecord[]
}

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

function HtmlContent({ html, className = '' }: { html: string; className?: string }) {
  return <div className={`katex-content ${className}`} dangerouslySetInnerHTML={{ __html: html }} />
}

export default function QuestionCard({ question, revealed, onChoiceResult, favorited, onToggleFavorite, wrongRecords }: Props) {
  const cardRef = useRef<HTMLDivElement>(null)
  const [selectedChoice, setSelectedChoice] = useState<string | null>(null)
  const [showChoiceFeedback, setShowChoiceFeedback] = useState(false)
  const store = useAppStore()

  const choices = useMemo(() => parseChoices(question), [question])
  const correctLetter = useMemo(() => (choices ? parseCorrectLetter(question.correctAnswer) : null), [choices, question.correctAnswer])

  // Read favorited from store, fall back to prop
  const isFavorited = store.cards.find((c) => c.questionId === question.id)?.favorited ?? favorited ?? false

  // Read wrongRecords from store, fall back to prop
  const cardWrongRecords = store.cards.find((c) => c.questionId === question.id)?.wrongRecords ?? wrongRecords ?? []

  const handleToggleFavorite = () => {
    if (onToggleFavorite) {
      onToggleFavorite()
    } else {
      store.toggleFavorite(question.id)
    }
  }

  const problemWithoutChoices = useMemo(() => {
    if (!choices) return question.problem
    let text = question.problem
    text = text.replace(/\(([A-D])\)\s*.+?(?=\s*\([A-D]\)|$)/gs, '')
    text = text.replace(/^>\s*/gm, '')
    return text.trim()
  }, [choices, question.problem])

  const isCorrect = selectedChoice === correctLetter

  const handleSelect = (letter: string) => {
    if (showChoiceFeedback) return
    setSelectedChoice(letter)
    setShowChoiceFeedback(true)
    onChoiceResult?.(letter, letter === correctLetter)
  }

  useEffect(() => {
    setSelectedChoice(null)
    setShowChoiceFeedback(false)
  }, [question.id])

  useEffect(() => {
    cardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [question.id])

  const problemHtml = renderContent(problemWithoutChoices)
  const stepsHtml = renderContent(question.steps)
  const wrongAnswerHtml = renderContent(question.wrongAnswer)
  const correctAnswerHtml = renderContent(question.correctAnswer)
  const summaryHtml = renderContent(question.summary)

  return (
    <div ref={cardRef} className="space-y-5">
      {/* Problem card */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow duration-300 overflow-hidden">
        <div className="px-6 py-3.5 border-b border-slate-100 bg-gradient-to-r from-slate-50 to-white flex items-center gap-2.5 flex-wrap">
          <BookOpen size={16} className="text-indigo-500" />
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">原题</span>
          {question.knowledgePoints?.map((kp) => (
            <span key={kp} className="text-[10px] px-1.5 py-0.5 rounded-full bg-indigo-50 text-indigo-600 font-medium hover:bg-indigo-100 transition-colors cursor-default">
              {kp}
            </span>
          ))}
          <div className="flex-1" />
          {onToggleFavorite !== undefined && (
            <button onClick={handleToggleFavorite}
              className="p-1 rounded-full hover:bg-amber-100 transition-all duration-200 hover:scale-110 active:scale-90"
              title={isFavorited ? '取消收藏' : '收藏'}>
              <Star size={16} className={isFavorited ? 'fill-amber-400 text-amber-400' : 'text-slate-300 hover:text-amber-400 transition-colors'} />
            </button>
          )}
        </div>
        <div className="px-6 py-5">
          {question.image && (
            <img src={question.image} alt="原题图片"
              className="w-full max-h-64 object-contain rounded-lg border border-slate-200 mb-4" />
          )}
          <HtmlContent html={problemHtml} className="text-[15px] text-slate-700 leading-loose" />

          {/* Choice buttons */}
          {choices && (
            <div className="mt-4 space-y-2">
              {choices.map((ch) => {
                let btnStyle = 'border-slate-200 bg-white hover:border-indigo-300 hover:bg-indigo-50 hover:scale-[1.01] text-slate-700 shadow-sm hover:shadow'
                if (showChoiceFeedback) {
                  if (ch.letter === correctLetter) {
                    btnStyle = 'border-green-400 bg-green-50 text-green-700 ring-1 ring-green-400 shadow-sm'
                  } else if (ch.letter === selectedChoice && !isCorrect) {
                    btnStyle = 'border-red-400 bg-red-50 text-red-700 ring-1 ring-red-400 shadow-sm'
                  } else {
                    btnStyle = 'border-slate-100 bg-slate-50 text-slate-400'
                  }
                }
                return (
                  <button
                    key={ch.letter}
                    onClick={() => handleSelect(ch.letter)}
                    disabled={showChoiceFeedback}
                    className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl border-2 text-left transition-all duration-200 ${btnStyle} ${
                      !showChoiceFeedback ? 'active:scale-[0.98] cursor-pointer' : 'cursor-default'
                    }`}
                  >
                    <span className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 transition-colors duration-200 ${
                      showChoiceFeedback && ch.letter === correctLetter
                        ? 'bg-green-500 text-white'
                        : showChoiceFeedback && ch.letter === selectedChoice && !isCorrect
                        ? 'bg-red-500 text-white'
                        : 'bg-slate-100 text-slate-500'
                    }`}>
                      {showChoiceFeedback && ch.letter === correctLetter ? <Check size={13} /> : ch.letter}
                    </span>
                    <span className="text-sm leading-relaxed" dangerouslySetInnerHTML={{ __html: renderContent(ch.text) }} />
                    {showChoiceFeedback && ch.letter === correctLetter && (
                      <Check size={16} className="text-green-500 ml-auto flex-shrink-0 animate-bounce-in" />
                    )}
                    {showChoiceFeedback && ch.letter === selectedChoice && !isCorrect && (
                      <X size={16} className="text-red-400 ml-auto flex-shrink-0 animate-bounce-in" />
                    )}
                  </button>
                )
              })}
            </div>
          )}

          {/* Choice feedback toast */}
          {showChoiceFeedback && (
            <div className={`mt-4 px-4 py-3 rounded-xl flex items-center gap-2.5 animate-slide-up ${
              isCorrect ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
            }`}>
              {isCorrect ? (
                <>
                  <CheckCircle2 size={18} className="text-green-500 flex-shrink-0" />
                  <span className="text-sm font-medium text-green-700">回答正确！</span>
                </>
              ) : (
                <>
                  <AlertTriangle size={18} className="text-red-500 flex-shrink-0" />
                  <span className="text-sm font-medium text-red-700">
                    回答错误，正确答案是 <strong>{correctLetter}</strong>
                  </span>
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Revealed content */}
      {revealed && (
        <div className="space-y-5 animate-slide-up">
          {/* Wrong archive — unified: original record + history */}
          <div className="bg-white rounded-xl border border-red-200 shadow-sm hover:shadow-md transition-shadow duration-300 overflow-hidden">
            <div className="px-6 py-3 border-b border-red-100 bg-gradient-to-r from-red-50 to-white flex items-center gap-2.5">
              <AlertTriangle size={15} className="text-red-500" />
              <span className="text-xs font-semibold text-red-600 uppercase tracking-wider">错误档案</span>
            </div>
            <div className="px-6 py-4 space-y-4">
              {/* Original record */}
              <div>
                <span className="text-[10px] text-slate-400">原始记录</span>
                <div className="mt-1.5">
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">错误答案</span>
                  <div className="mt-1">
                    <HtmlContent html={wrongAnswerHtml} className="text-sm text-red-700 leading-relaxed" />
                  </div>
                </div>
                <div className="mt-2">
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">错误原因</span>
                  <p className="text-sm text-slate-600 mt-1 leading-relaxed">{question.wrongReason}</p>
                </div>
              </div>

              {/* Historical review records */}
              {cardWrongRecords && cardWrongRecords.length > 0 && (
                <>
                  <div className="border-t border-red-100 pt-4">
                    <span className="text-[10px] font-semibold text-red-400 uppercase tracking-wider">
                      历史复习记录（{cardWrongRecords.length}次）
                    </span>
                  </div>
                  {[...cardWrongRecords].reverse().map((rec, i) => (
                    <div key={i} className={`${i > 0 ? 'pt-4 border-t border-red-50' : ''}`}>
                      <span className="text-[10px] text-slate-400">{rec.date}</span>
                      <div className="mt-1.5">
                        <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">错误答案</span>
                        <div className="mt-1 text-sm text-red-700 leading-relaxed markdown-body"
                          dangerouslySetInnerHTML={{ __html: renderContent(rec.wrongAnswer || '（未填写）') }} />
                      </div>
                      <div className="mt-2">
                        <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">错误原因</span>
                        <div className="mt-1 text-sm text-slate-600 leading-relaxed markdown-body"
                          dangerouslySetInnerHTML={{ __html: renderContent(rec.wrongReason || '（未填写）') }} />
                      </div>
                    </div>
                  ))}
                </>
              )}

              {/* ── Feature: Wrong Records Comparison (≥2 records) ── */}
              {cardWrongRecords && cardWrongRecords.length >= 2 && (
                <div className="border-t border-red-100 pt-4">
                  <span className="text-[10px] font-semibold text-amber-600 uppercase tracking-wider flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-amber-400" />错题对比
                  </span>
                  <div className="grid grid-cols-2 gap-3 mt-2">
                    {/* First mistake */}
                    <div className="bg-red-50/50 rounded-lg p-3 border border-red-100">
                      <span className="text-[9px] font-bold text-red-400 uppercase">第一次犯错</span>
                      <p className="text-[10px] text-slate-400 mt-0.5">{cardWrongRecords[cardWrongRecords.length - 1].date}</p>
                      <div className="mt-2">
                        <span className="text-[9px] font-semibold text-slate-400">错误答案</span>
                        <div className="mt-0.5 text-xs text-slate-600 leading-relaxed"
                          dangerouslySetInnerHTML={{ __html: renderContent(cardWrongRecords[cardWrongRecords.length - 1].wrongAnswer || '（未填写）') }} />
                      </div>
                      <div className="mt-1.5">
                        <span className="text-[9px] font-semibold text-slate-400">错误原因</span>
                        <div className="mt-0.5 text-xs text-slate-600 leading-relaxed"
                          dangerouslySetInnerHTML={{ __html: renderContent(cardWrongRecords[cardWrongRecords.length - 1].wrongReason || '（未填写）') }} />
                      </div>
                    </div>
                    {/* Latest mistake */}
                    <div className="bg-orange-50/50 rounded-lg p-3 border border-orange-200">
                      <span className="text-[9px] font-bold text-orange-500 uppercase">最近一次犯错</span>
                      <p className="text-[10px] text-slate-400 mt-0.5">{cardWrongRecords[0].date}</p>
                      <div className="mt-2">
                        <span className="text-[9px] font-semibold text-slate-400">错误答案</span>
                        <div className="mt-0.5 text-xs text-slate-600 leading-relaxed"
                          dangerouslySetInnerHTML={{ __html: renderContent(cardWrongRecords[0].wrongAnswer || '（未填写）') }} />
                      </div>
                      <div className="mt-1.5">
                        <span className="text-[9px] font-semibold text-slate-400">错误原因</span>
                        <div className="mt-0.5 text-xs text-slate-600 leading-relaxed"
                          dangerouslySetInnerHTML={{ __html: renderContent(cardWrongRecords[0].wrongReason || '（未填写）') }} />
                      </div>
                    </div>
                  </div>
                  {/* Diff highlight */}
                  {cardWrongRecords[cardWrongRecords.length - 1].wrongReason !== cardWrongRecords[0].wrongReason && (
                    <div className="mt-3 px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg">
                      <span className="text-[9px] font-bold text-amber-600 uppercase">变化分析</span>
                      <p className="text-xs text-slate-600 mt-1">
                        错误原因从「{cardWrongRecords[cardWrongRecords.length - 1].wrongReason || '未记录'}」变为「{cardWrongRecords[0].wrongReason || '未记录'}」
                        {cardWrongRecords.length > 2 && <span className="text-amber-500 ml-1">（共犯了 {cardWrongRecords.length} 次）</span>}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Correct answer */}
          <div className="bg-white rounded-xl border border-green-200 shadow-sm hover:shadow-md transition-shadow duration-300 overflow-hidden">
            <div className="px-6 py-3 border-b border-green-100 bg-gradient-to-r from-green-50 to-white flex items-center gap-2.5">
              <CheckCircle2 size={15} className="text-green-500" />
              <span className="text-xs font-semibold text-green-600 uppercase tracking-wider">正确解析</span>
            </div>
            <div className="px-6 py-4 space-y-4">
              <div>
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">正确答案</span>
                <div className="mt-1.5">
                  <HtmlContent html={correctAnswerHtml} className="text-sm text-green-700 font-medium leading-relaxed" />
                </div>
              </div>
              <div>
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">核心步骤</span>
                <div className="mt-1.5">
                  <HtmlContent html={stepsHtml} className="text-sm text-slate-600 leading-loose" />
                </div>
              </div>
            </div>
          </div>

          {/* One-line summary */}
          {question.summary && question.summary !== '（无总结）' && (
            <div className="bg-amber-50 rounded-xl border border-amber-200 p-5 flex items-start gap-3 hover:shadow-md transition-shadow duration-300">
              <Lightbulb size={17} className="text-amber-500 flex-shrink-0 mt-0.5" />
              <div>
                <span className="text-[11px] font-semibold text-amber-700 uppercase tracking-wider">一句话总结</span>
                <div className="mt-1">
                  <HtmlContent html={summaryHtml} className="text-sm text-amber-800 leading-relaxed" />
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
