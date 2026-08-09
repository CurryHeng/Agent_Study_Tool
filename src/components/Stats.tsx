import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { CalendarDays, TrendingUp, Target, Award, ChevronRight, Clock } from 'lucide-react'
import questionsData from '../data/questions.json'
import { loadCards, loadLogs, loadUserQuestions } from '../lib/storage'
import { useAppStore } from '../lib/store'

export default function Stats() {
  const navigate = useNavigate()
  const store = useAppStore()
  const cards = store.cards
  const logs = store.logs

  useEffect(() => {
    // Legacy sync: load from old localStorage keys and sync into store on first mount
    const legacyCards = loadCards()
    const legacyLogs = loadLogs()
    const legacyUserQs = loadUserQuestions()
    if (store.cards.length === 0 && legacyCards.length > 0) store.setCards(legacyCards)
    if (store.logs.length === 0 && legacyLogs.length > 0) store.setLogs(legacyLogs)
    if (store.userQuestions.length === 0 && legacyUserQs.length > 0) store.setUserQuestions(legacyUserQs)
  }, [])

  const questions = [...questionsData, ...store.userQuestions]

  // Calculate streak (consecutive days with reviews)
  const reviewDates = [...new Set(logs.map((l) => l.date))].sort().reverse()
  let streak = 0
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  for (let i = 0; i < reviewDates.length; i++) {
    const d = new Date(reviewDates[i])
    d.setHours(0, 0, 0, 0)
    const expected = new Date(today)
    expected.setDate(expected.getDate() - i)
    if (d.getTime() === expected.getTime()) {
      streak++
    } else {
      break
    }
  }

  // Ratings distribution
  const ratingCounts = { again: 0, hard: 0, good: 0, easy: 0 }
  for (const log of logs) {
    if (log.rating in ratingCounts) ratingCounts[log.rating as keyof typeof ratingCounts]++
  }

  const totalReviews = logs.length
  const masteredRate =
    totalReviews > 0
      ? Math.round(((ratingCounts.good + ratingCounts.easy) / totalReviews) * 100)
      : 0

  // Choice accuracy
  const choiceLogs = logs.filter((l) => l.choiceCorrect !== undefined)
  const choiceCorrect = choiceLogs.filter((l) => l.choiceCorrect).length
  const choiceRate = choiceLogs.length > 0 ? Math.round((choiceCorrect / choiceLogs.length) * 100) : null

  // Reviews per day (last 7 days)
  const last7Days: { date: string; count: number }[] = []
  for (let i = 6; i >= 0; i--) {
    const d = new Date(today)
    d.setDate(d.getDate() - i)
    const dateStr = d.toISOString().split('T')[0]
    const count = logs.filter((l) => l.date === dateStr).length
    last7Days.push({ date: dateStr, count })
  }
  const maxCount = Math.max(...last7Days.map((d) => d.count), 1)

  // Recent history (latest 100)
  const recentLogs = [...logs].sort((a, b) => b.date.localeCompare(a.date) || logs.indexOf(b) - logs.indexOf(a)).slice(0, 100)

  // Per-question accuracy buckets for chart
  const reviewedCards = cards.filter((c) => c.totalAttempts > 0)
  const buckets = [
    { label: '0-19%', min: 0, max: 19, color: 'bg-red-400', count: 0 },
    { label: '20-39%', min: 20, max: 39, color: 'bg-orange-400', count: 0 },
    { label: '40-59%', min: 40, max: 59, color: 'bg-amber-400', count: 0 },
    { label: '60-79%', min: 60, max: 79, color: 'bg-lime-400', count: 0 },
    { label: '80-100%', min: 80, max: 100, color: 'bg-emerald-400', count: 0 },
  ]
  for (const c of reviewedCards) {
    const rate = Math.round((c.totalCorrect / c.totalAttempts) * 100)
    for (const b of buckets) {
      if (rate >= b.min && rate <= b.max) { b.count++; break }
    }
  }
  const maxBucket = Math.max(...buckets.map((b) => b.count), 1)

  // ── Feature: Knowledge Point Heatmap ──
  const kpStats: Record<string, { total: number; errors: number }> = {}
  for (const q of questions) {
    if (!q.knowledgePoints || q.knowledgePoints.length === 0) continue
    for (const kp of q.knowledgePoints) {
      if (!kpStats[kp]) kpStats[kp] = { total: 0, errors: 0 }
      const qLogs = logs.filter((l) => l.questionId === q.id)
      kpStats[kp].total += qLogs.length
      kpStats[kp].errors += qLogs.filter((l) => l.rating === 'again' || l.rating === 'hard').length
    }
  }
  const kpEntries = Object.entries(kpStats)
    .filter(([, s]) => s.total > 0)
    .sort((a, b) => {
      const rateA = a[1].total > 0 ? a[1].errors / a[1].total : 0
      const rateB = b[1].total > 0 ? b[1].errors / b[1].total : 0
      return rateB - rateA
    })

  // ── Feature: Wrong Reason Pie Chart ──
  const reasonCategories: Record<string, number> = {
    '计算错误': 0,
    '概念不清': 0,
    '公式记错': 0,
    '看错题': 0,
    '其他': 0,
  }
  const allReasons: string[] = []
  for (const q of questions) {
    if (q.wrongReason && q.wrongReason !== '（未记录）') allReasons.push(q.wrongReason)
  }
  for (const c of cards) {
    for (const wr of c.wrongRecords || []) {
      if (wr.wrongReason) allReasons.push(wr.wrongReason)
    }
  }
  for (const reason of allReasons) {
    const lower = reason
    if (/计算|算错|运算|粗心算错/.test(lower)) reasonCategories['计算错误']++
    else if (/概念|定义|理解偏差|本质/.test(lower)) reasonCategories['概念不清']++
    else if (/公式|记错|忘记公式|定理|记混/.test(lower)) reasonCategories['公式记错']++
    else if (/看错|看漏|漏看|审题|读题|马虎/.test(lower)) reasonCategories['看错题']++
    else reasonCategories['其他']++
  }
  const reasonTotal = Object.values(reasonCategories).reduce((a, b) => a + b, 0)
  const reasonEntries = Object.entries(reasonCategories)
    .filter(([, c]) => c > 0)
    .sort((a, b) => b[1] - a[1])
  const REASON_COLORS: Record<string, { bg: string; dot: string }> = {
    '计算错误': { bg: 'bg-red-400', dot: 'bg-red-500' },
    '概念不清': { bg: 'bg-orange-400', dot: 'bg-orange-500' },
    '公式记错': { bg: 'bg-amber-400', dot: 'bg-amber-500' },
    '看错题': { bg: 'bg-blue-400', dot: 'bg-blue-500' },
    '其他': { bg: 'bg-slate-400', dot: 'bg-slate-500' },
  }

  // ── Feature: Time Tracking (本周) ──
  const now2 = new Date()
  const dayOfWeek = now2.getDay()
  const mondayOffset = dayOfWeek === 0 ? -6 : 1 - dayOfWeek
  const monday = new Date(now2)
  monday.setDate(now2.getDate() + mondayOffset)
  monday.setHours(0, 0, 0, 0)
  const sunday = new Date(monday)
  sunday.setDate(monday.getDate() + 6)
  sunday.setHours(23, 59, 59, 999)
  const weekLogs = logs.filter((l) => {
    const d = new Date(l.date)
    return d >= monday && d <= sunday
  })
  const weekSeconds = weekLogs.reduce((sum, l) => sum + (l.timeSpent || 0), 0)
  const weekMinutes = Math.round(weekSeconds / 60)
  const daysWithReviews = new Set(weekLogs.map((l) => l.date)).size
  const dailyAvg = daysWithReviews > 0 ? Math.round(weekMinutes / daysWithReviews) : 0

  const RATING_LABEL: Record<string, { label: string; color: string; bg: string }> = {
    again: { label: '忘记', color: 'text-red-600', bg: 'bg-red-100' },
    hard: { label: '困难', color: 'text-orange-600', bg: 'bg-orange-100' },
    good: { label: '正确', color: 'text-emerald-600', bg: 'bg-emerald-100' },
    easy: { label: '简单', color: 'text-blue-600', bg: 'bg-blue-100' },
  }

  return (
    <div className="space-y-5 animate-fade-in">
      <h1 className="text-xl font-bold text-slate-800">学习统计</h1>

      {/* Big numbers */}
      <div className="grid grid-cols-2 gap-3">
        <StatBox icon={<CalendarDays size={20} />} label="连续学习" value={`${streak} 天`} color="text-blue-500 bg-blue-50" />
        <StatBox icon={<TrendingUp size={20} />} label="总复习次数" value={`${totalReviews}`} color="text-green-500 bg-green-50" />
        <StatBox icon={<Target size={20} />} label="掌握率" value={`${masteredRate}%`} color="text-purple-500 bg-purple-50" />
        <StatBox icon={<Award size={20} />} label="题库规模" value={`${questions.length} 题`} color="text-orange-500 bg-orange-50" />
        {choiceRate !== null && (
          <StatBox icon={<Target size={20} />} label="选择题正确率" value={`${choiceRate}%`} color="text-cyan-500 bg-cyan-50" />
        )}
      </div>

      {/* Ratings breakdown */}
      {totalReviews > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
          <h3 className="font-semibold text-sm text-slate-800 mb-4">掌握分布</h3>
          <div className="h-3 bg-slate-100 rounded-full overflow-hidden flex">
            {[
              { key: 'again', count: ratingCounts.again, color: 'bg-red-400' },
              { key: 'hard', count: ratingCounts.hard, color: 'bg-orange-400' },
              { key: 'good', count: ratingCounts.good, color: 'bg-emerald-400' },
              { key: 'easy', count: ratingCounts.easy, color: 'bg-blue-400' },
            ].map(({ key, count, color }) =>
              count > 0 ? (
                <div
                  key={key}
                  className={`${color} h-full transition-all`}
                  style={{ width: `${(count / totalReviews) * 100}%` }}
                  title={`${key}: ${count}`}
                />
              ) : null
            )}
          </div>
          <div className="flex justify-between mt-3 text-xs text-slate-500">
            <span>忘记 {ratingCounts.again}</span>
            <span>困难 {ratingCounts.hard}</span>
            <span>正确 {ratingCounts.good}</span>
            <span>简单 {ratingCounts.easy}</span>
          </div>
        </div>
      )}

      {/* Last 7 days bar chart */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
        <h3 className="font-semibold text-sm text-slate-800 mb-4">最近 7 天复习量</h3>
        <div className="flex items-end gap-2 h-32">
          {last7Days.map((d) => (
            <div key={d.date} className="flex-1 flex flex-col items-center gap-1.5 h-full justify-end">
              <span className="text-[10px] text-slate-400 tabular-nums">{d.count}</span>
              <div
                className="w-full bg-indigo-500 rounded-t-md transition-all duration-500 min-h-[4px]"
                style={{ height: `${(d.count / maxCount) * 100}%` }}
              />
              <span className="text-[9px] text-slate-400 tabular-nums">
                {new Date(d.date).toLocaleDateString('zh-CN', { weekday: 'short' }).replace('周', '')}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Accuracy distribution chart */}
      {reviewedCards.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
          <h3 className="font-semibold text-sm text-slate-800 mb-4">
            单题正确率分布
            <span className="text-xs text-slate-400 font-normal ml-1">（{reviewedCards.length} 道已刷题目）</span>
          </h3>
          <div className="flex items-end gap-3 h-40">
            {buckets.map((b) => (
              <div key={b.label} className="flex-1 flex flex-col items-center gap-1.5 h-full justify-end">
                <span className="text-xs font-medium text-slate-600 tabular-nums">{b.count}</span>
                <div
                  className={`w-full ${b.color} rounded-t-lg transition-all duration-500 min-h-[4px]`}
                  style={{ height: `${(b.count / maxBucket) * 100}%` }}
                />
                <span className="text-[10px] text-slate-400 tabular-nums whitespace-nowrap">{b.label}</span>
              </div>
            ))}
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 flex justify-between text-[10px] text-slate-400">
            <span>低正确率</span>
            <span>高正确率</span>
          </div>
        </div>
      )}

      {/* ── Feature: Time Tracking (本周学习时长) ── */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
        <h3 className="font-semibold text-sm text-slate-800 mb-3 flex items-center gap-2">
          <Clock size={15} className="text-indigo-500" />本周学习时长
        </h3>
        <div className="flex gap-4">
          <div className="flex-1 bg-indigo-50 rounded-xl p-3 text-center">
            <p className="text-2xl font-bold text-indigo-600">{weekMinutes}</p>
            <p className="text-[10px] text-indigo-400 mt-0.5">累计分钟</p>
          </div>
          <div className="flex-1 bg-purple-50 rounded-xl p-3 text-center">
            <p className="text-2xl font-bold text-purple-600">{dailyAvg}</p>
            <p className="text-[10px] text-purple-400 mt-0.5">日均分钟</p>
          </div>
          <div className="flex-1 bg-emerald-50 rounded-xl p-3 text-center">
            <p className="text-2xl font-bold text-emerald-600">{daysWithReviews}</p>
            <p className="text-[10px] text-emerald-400 mt-0.5">学习天数</p>
          </div>
        </div>
        {weekMinutes === 0 && (
          <p className="text-[10px] text-slate-400 mt-3 text-center">本周暂无学习记录，快去刷题吧！</p>
        )}
      </div>

      {/* ── Feature: Knowledge Point Heatmap ── */}
      {kpEntries.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
          <h3 className="font-semibold text-sm text-slate-800 mb-4">
            知识点掌握热力图
            <span className="text-xs text-slate-400 font-normal ml-1">（错误率越高颜色越深）</span>
          </h3>
          <div className="flex flex-wrap gap-2">
            {kpEntries.map(([kp, stats]) => {
              const rate = stats.total > 0 ? stats.errors / stats.total : 0
              let cellColor = 'bg-emerald-100 text-emerald-700 border-emerald-200'
              if (rate > 0.5) cellColor = 'bg-red-100 text-red-700 border-red-300'
              else if (rate >= 0.3) cellColor = 'bg-orange-100 text-orange-700 border-orange-200'
              return (
                <div
                  key={kp}
                  className={`px-3 py-2 rounded-lg border text-xs font-medium flex items-center gap-2 ${cellColor} transition-colors hover:scale-105 cursor-default`}
                  title={`${kp}: 错误 ${stats.errors}/${stats.total} (${Math.round(rate * 100)}%)`}
                >
                  <span className="max-w-[120px] truncate">{kp}</span>
                  <span className="tabular-nums opacity-70">{Math.round(rate * 100)}%</span>
                </div>
              )
            })}
          </div>
          <div className="flex items-center gap-3 mt-4 pt-3 border-t border-slate-100 text-[10px] text-slate-400">
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-red-100 border border-red-300" /> &gt;50%</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-orange-100 border border-orange-200" /> 30-50%</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-emerald-100 border border-emerald-200" /> &lt;30%</span>
          </div>
        </div>
      )}

      {/* ── Feature: Wrong Reason Pie Chart ── */}
      {reasonTotal > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
          <h3 className="font-semibold text-sm text-slate-800 mb-4">
            错因分类分析
            <span className="text-xs text-slate-400 font-normal ml-1">（共 {reasonTotal} 条错因记录）</span>
          </h3>
          <div className="flex flex-col sm:flex-row items-center gap-6">
            {/* CSS Pie */}
            <div className="relative w-36 h-36 flex-shrink-0">
              <svg viewBox="0 0 36 36" className="w-full h-full transform -rotate-90">
                {(() => {
                  let cumulative = 0
                  return reasonEntries.map(([cat, count]) => {
                    const pct = (count / reasonTotal) * 100
                    const startAngle = (cumulative / 100) * 360
                    const endAngle = startAngle + (pct / 100) * 360
                    cumulative += pct
                    const x1 = 18 + 15.9 * Math.cos((startAngle * Math.PI) / 180)
                    const y1 = 18 + 15.9 * Math.sin((startAngle * Math.PI) / 180)
                    const x2 = 18 + 15.9 * Math.cos((endAngle * Math.PI) / 180)
                    const y2 = 18 + 15.9 * Math.sin((endAngle * Math.PI) / 180)
                    const largeArc = pct > 50 ? 1 : 0
                    const color = REASON_COLORS[cat]?.dot || 'bg-slate-500'
                    const strokeColor = color.replace('bg-', '#').replace('-500', '').replace('-400', '')
                    // Map tailwind colors to hex
                    const hexMap: Record<string, string> = {
                      'red': '#f87171', 'orange': '#fb923c', 'amber': '#fbbf24',
                      'blue': '#60a5fa', 'slate': '#94a3b8',
                    }
                    const hex = hexMap[strokeColor] || '#94a3b8'
                    return (
                      <path
                        key={cat}
                        d={`M18 18 L${x1} ${y1} A15.9 15.9 0 ${largeArc} 1 ${x2} ${y2} Z`}
                        fill={hex}
                        className="transition-all duration-300 hover:opacity-80"
                      />
                    )
                  })
                })()}
                <circle cx="18" cy="18" r="8" fill="white" />
              </svg>
            </div>
            {/* Legend */}
            <div className="flex-1 space-y-2">
              {reasonEntries.map(([cat, count]) => {
                const pct = Math.round((count / reasonTotal) * 100)
                const colors = REASON_COLORS[cat] || { bg: 'bg-slate-400', dot: 'bg-slate-500' }
                return (
                  <div key={cat} className="flex items-center gap-2">
                    <span className={`w-3 h-3 rounded-full flex-shrink-0 ${colors.dot}`} />
                    <span className="text-sm text-slate-700 flex-1">{cat}</span>
                    <span className="text-sm font-semibold text-slate-800 tabular-nums">{count}</span>
                    <span className="text-xs text-slate-400 tabular-nums w-8 text-right">{pct}%</span>
                    <div className="w-20 h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div className={`h-full ${colors.bg} rounded-full transition-all duration-500`} style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}

      {/* Review history */}
      {recentLogs.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-100">
            <h3 className="font-semibold text-sm text-slate-800">
              复习历史
              <span className="text-xs text-slate-400 font-normal ml-1">（最近 {recentLogs.length} 条）</span>
            </h3>
          </div>
          <div className="divide-y divide-slate-50 max-h-96 overflow-y-auto">
            {recentLogs.map((log, i) => {
              const q = questions.find((q) => q.id === log.questionId)
              const r = RATING_LABEL[log.rating] || { label: log.rating, color: 'text-slate-500', bg: 'bg-slate-100' }
              return (
                <button
                  key={i}
                  onClick={() => navigate(`/review?ids=${log.questionId}`)}
                  className="w-full px-5 py-3 flex items-center gap-3 hover:bg-slate-50 transition-colors text-left"
                >
                  <span className="text-[10px] text-slate-400 w-20 flex-shrink-0 tabular-nums">{log.date}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-700 truncate">
                      {q ? `${q.chapter} · 错题${q.questionNumber}` : `题目 ${log.questionId}`}
                    </p>
                    {log.choiceCorrect !== undefined && (
                      <p className="text-[10px] text-slate-400 mt-0.5">
                        选择: {log.choiceSelected || '未选择'}
                        {log.choiceCorrect !== undefined && (log.choiceCorrect ? ' ✓' : ' ✗')}
                      </p>
                    )}
                  </div>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium flex-shrink-0 ${r.bg} ${r.color}`}>
                    {r.label}
                  </span>
                  {log.mode && (
                    <span className="text-[9px] text-slate-400 flex-shrink-0 hidden sm:inline">
                      {log.mode === 'relaxed' ? '宽松' : log.mode === 'normal' ? '普通' : '严格'}
                    </span>
                  )}
                  <ChevronRight size={14} className="text-slate-300 flex-shrink-0" />
                </button>
              )
            })}
          </div>
        </div>
      )}

      {totalReviews === 0 && (
        <div className="text-center py-12 text-slate-400">
          <p className="text-sm">还没有复习记录</p>
          <p className="text-xs mt-1">开始刷题后这里会显示统计数据</p>
        </div>
      )}
    </div>
  )
}

function StatBox({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode
  label: string
  value: string
  color: string
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
      <div className={`w-9 h-9 rounded-lg ${color} flex items-center justify-center mb-2`}>
        {icon}
      </div>
      <p className="text-xl font-bold text-slate-800">{value}</p>
      <p className="text-xs text-slate-400 mt-0.5">{label}</p>
    </div>
  )
}
