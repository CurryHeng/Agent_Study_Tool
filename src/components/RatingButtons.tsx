import type { Rating, ReviewCard } from '../types'
import { getNextReviewLabel } from '../lib/sm2'

interface Props {
  onRate: (rating: Rating) => void
  card: ReviewCard
  allowedRatings?: Rating[]
}

const ratings: { key: Rating; label: string; desc: string; color: string; shortcut: string }[] = [
  { key: 'again', label: '忘记', desc: '完全不会', color: 'bg-red-500 hover:bg-red-600 active:bg-red-700', shortcut: '1' },
  { key: 'hard', label: '困难', desc: '想起来了但很费劲', color: 'bg-orange-400 hover:bg-orange-500 active:bg-orange-600', shortcut: '2' },
  { key: 'good', label: '正确', desc: '正常回忆起来了', color: 'bg-emerald-500 hover:bg-emerald-600 active:bg-emerald-700', shortcut: '3' },
  { key: 'easy', label: '简单', desc: '非常轻松', color: 'bg-blue-500 hover:bg-blue-600 active:bg-blue-700', shortcut: '4' },
]

export default function RatingButtons({ onRate, card, allowedRatings }: Props) {
  const displayRatings = allowedRatings ? ratings.filter((r) => allowedRatings.includes(r.key)) : ratings
  const cols = displayRatings.length <= 2 ? 'grid-cols-2' : 'grid-cols-4'
  return (
    <div className="space-y-2">
      <p className="text-xs text-slate-400 text-center">评价你的掌握程度</p>
      <div className={`grid ${cols} gap-2`}>
        {displayRatings.map((r) => (
          <button
            key={r.key}
            onClick={() => onRate(r.key)}
            className={`${r.color} text-white rounded-xl py-3 px-2 flex flex-col items-center gap-0.5 transition-all active:scale-[0.95] shadow-sm`}
          >
            <span className="text-sm font-bold">{r.label}</span>
            <span className="text-[10px] opacity-80 leading-tight text-center">{r.desc}</span>
            <span className="text-[9px] opacity-50 mt-0.5">{r.shortcut}</span>
          </button>
        ))}
      </div>
      <p className="text-[10px] text-slate-300 text-center">
        下次复习：{getNextReviewLabel(card)}
      </p>
    </div>
  )
}
