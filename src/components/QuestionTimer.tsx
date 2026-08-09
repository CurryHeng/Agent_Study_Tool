import { useEffect, useRef, useState } from 'react'
import { Clock } from 'lucide-react'

interface Props {
  seconds: number
  onTimeout?: () => void
  running: boolean
  countUp?: boolean
  className?: string
}

export default function QuestionTimer({ seconds, onTimeout, running, countUp, className = '' }: Props) {
  const [elapsed, setElapsed] = useState(0)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const timedOutRef = useRef(false)

  useEffect(() => {
    if (running) {
      intervalRef.current = setInterval(() => {
        setElapsed((prev) => prev + 1)
      }, 1000)
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [running])

  // Reset when seconds changes
  useEffect(() => {
    setElapsed(0)
    timedOutRef.current = false
  }, [seconds])

  useEffect(() => {
    if (!countUp && running && elapsed >= seconds && !timedOutRef.current) {
      timedOutRef.current = true
      onTimeout?.()
    }
  }, [elapsed, seconds, countUp, running, onTimeout])

  if (countUp) {
    const m = Math.floor(elapsed / 60)
    const s = elapsed % 60
    const display = `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
    return (
      <div className={`flex items-center gap-1.5 text-sm font-mono tabular-nums ${className}`}>
        <Clock size={14} />
        <span>{display}</span>
      </div>
    )
  }

  const remaining = Math.max(0, seconds - elapsed)
  const m = Math.floor(remaining / 60)
  const s = remaining % 60
  const display = `${m}:${s.toString().padStart(2, '0')}`
  const pct = (remaining / seconds) * 100
  const urgent = remaining < 60

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className="flex-1 h-1.5 bg-slate-200 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-1000 ${urgent ? 'bg-red-500' : 'bg-indigo-500'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={`text-xs font-mono tabular-nums font-medium ${urgent ? 'text-red-500' : 'text-slate-500'}`}>
        {display}
      </span>
    </div>
  )
}
