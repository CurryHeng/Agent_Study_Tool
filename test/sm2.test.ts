/**
 * SM-2 间隔重复算法测试
 * 
 * 运行方式：npx vitest run test/sm2.test.ts
 */

import { describe, it, expect } from 'vitest'

// 直接复制核心逻辑，避免依赖项目构建
const DEFAULT_EASE = 2.5
const MIN_EASE = 1.3
const EASE_BONUS = 0.15
const EASE_PENALTY = 0.2

interface ReviewCard {
  questionId: string
  ease: number
  interval: number
  repetitions: number
  totalAttempts: number
  totalCorrect: number
  nextReview: string
  lastReview: string | null
  favorited: boolean
  wrongRecords: any[]
}

function createCard(questionId: string): ReviewCard {
  return {
    questionId,
    ease: DEFAULT_EASE,
    interval: 0,
    repetitions: 0,
    nextReview: new Date().toISOString().split('T')[0],
    lastReview: null,
    totalAttempts: 0,
    totalCorrect: 0,
    favorited: false,
    wrongRecords: [],
  }
}

type Rating = 'again' | 'hard' | 'good' | 'easy'

function nextDay(date: Date, days: number): string {
  const d = new Date(date)
  d.setDate(d.getDate() + days)
  return d.toISOString().split('T')[0]
}

function reviewCard(card: ReviewCard, rating: Rating, isCorrect?: boolean, now: Date = new Date()): ReviewCard {
  const next: ReviewCard = {
    ...card,
    lastReview: now.toISOString().split('T')[0],
    totalAttempts: card.totalAttempts + 1,
    totalCorrect: isCorrect ? card.totalCorrect + 1 : card.totalCorrect,
  }

  if (rating === 'again') {
    next.repetitions = 0
    next.interval = 1
    next.ease = Math.max(MIN_EASE, card.ease - EASE_PENALTY)
  } else {
    next.repetitions = card.repetitions + 1

    if (card.repetitions === 0) {
      next.interval = 1
    } else if (card.repetitions === 1) {
      next.interval = 6
    } else {
      next.interval = Math.round(card.interval * card.ease)
    }

    if (rating === 'easy') {
      next.interval = Math.round(next.interval * 1.3)
      next.ease = card.ease + EASE_BONUS
    } else if (rating === 'hard') {
      next.interval = Math.max(Math.round(next.interval * 0.8), card.interval > 0 ? 1 : 0)
      next.ease = Math.max(MIN_EASE, card.ease - EASE_PENALTY * 0.5)
    }
  }

  next.nextReview = nextDay(now, next.interval || 1)
  return next
}

function getDueCards(cards: ReviewCard[]): ReviewCard[] {
  const today = new Date().toISOString().split('T')[0]
  return cards.filter((c) => c.nextReview <= today)
}

function getNextReviewLabel(card: ReviewCard): string {
  if (card.interval === 0) return '新题'
  if (card.interval < 1) return '<1天'
  if (card.interval === 1) return '1天'
  if (card.interval < 7) return `${card.interval}天`
  if (card.interval < 30) return `${Math.round(card.interval / 7)}周`
  return `${Math.round(card.interval / 30)}月`
}

// ====== Tests ======

describe('SM-2 createCard', () => {
  it('should create a card with default values', () => {
    const card = createCard('q1')
    expect(card.questionId).toBe('q1')
    expect(card.ease).toBe(2.5)
    expect(card.interval).toBe(0)
    expect(card.repetitions).toBe(0)
    expect(card.totalAttempts).toBe(0)
    expect(card.totalCorrect).toBe(0)
    expect(card.favorited).toBe(false)
    expect(card.lastReview).toBeNull()
    // nextReview should be today
    expect(card.nextReview).toBe(new Date().toISOString().split('T')[0])
  })
})

describe('SM-2 reviewCard', () => {
  it('"again" should reset repetitions to 0 and set interval to 1', () => {
    const card = createCard('q1')
    card.repetitions = 3
    card.interval = 30
    card.ease = 2.5

    const result = reviewCard(card, 'again', false)

    expect(result.repetitions).toBe(0)
    expect(result.interval).toBe(1)
    expect(result.totalAttempts).toBe(1)
    expect(result.totalCorrect).toBe(0)
    expect(result.ease).toBe(2.3) // 2.5 - 0.2
  })

  it('"again" should not drop ease below MIN_EASE', () => {
    const card = createCard('q1')
    card.ease = MIN_EASE // 1.3

    const result = reviewCard(card, 'again', false)

    expect(result.ease).toBe(MIN_EASE)
  })

  it('first "good" should set interval to 1', () => {
    const card = createCard('q1') // repetitions = 0, interval = 0

    const result = reviewCard(card, 'good', true)

    expect(result.repetitions).toBe(1)
    expect(result.interval).toBe(1)
    expect(result.totalCorrect).toBe(1)
  })

  it('second "good" should set interval to 6', () => {
    const card = createCard('q1')
    card.repetitions = 1
    card.interval = 1

    const result = reviewCard(card, 'good', true)

    expect(result.repetitions).toBe(2)
    expect(result.interval).toBe(6)
  })

  it('third "good" should multiply interval by ease', () => {
    const card = createCard('q1')
    card.repetitions = 2
    card.interval = 6
    card.ease = 2.5

    const result = reviewCard(card, 'good', true)

    expect(result.repetitions).toBe(3)
    expect(result.interval).toBe(15) // 6 * 2.5 = 15
  })

  it('"easy" should increase interval by 1.3x and boost ease', () => {
    const card = createCard('q1')
    card.repetitions = 2
    card.interval = 6
    card.ease = 2.5

    const result = reviewCard(card, 'easy', true)

    expect(result.interval).toBe(20) // 15 * 1.3 ≈ 19.5 → 20
    expect(result.ease).toBe(2.65) // 2.5 + 0.15
  })

  it('"hard" should reduce interval by 0.8x', () => {
    const card = createCard('q1')
    card.repetitions = 2
    card.interval = 6
    card.ease = 2.5

    const result = reviewCard(card, 'hard', false)

    // First: next.interval = Math.round(6 * 2.5) = 15
    // Then hard: next.interval = Math.max(Math.round(15 * 0.8), 1) = Math.max(12, 1) = 12
    expect(result.interval).toBe(12)
  })

  it('isCorrect should track accuracy', () => {
    const card = createCard('q1')

    const r1 = reviewCard(card, 'good', true)
    expect(r1.totalAttempts).toBe(1)
    expect(r1.totalCorrect).toBe(1)

    const r2 = reviewCard(r1, 'again', false)
    expect(r2.totalAttempts).toBe(2)
    expect(r2.totalCorrect).toBe(1)
  })

  it('nextReview should be set to correct future date', () => {
    const now = new Date('2025-06-01')
    const card = createCard('q1')
    card.repetitions = 2
    card.interval = 6
    card.ease = 2.5

    const result = reviewCard(card, 'good', true, now)

    // interval = 15, so nextReview = 2025-06-16
    expect(result.nextReview).toBe('2025-06-16')
  })
})

describe('SM-2 getDueCards', () => {
  it('should return cards due for review', () => {
    const today = new Date().toISOString().split('T')[0]
    const yesterday = nextDay(new Date(), -1)
    const tomorrow = nextDay(new Date(), 1)

    const cards: ReviewCard[] = [
      { ...createCard('q1'), nextReview: yesterday },
      { ...createCard('q2'), nextReview: today },
      { ...createCard('q3'), nextReview: tomorrow },
    ]

    const due = getDueCards(cards)
    expect(due).toHaveLength(2)
    expect(due.map((c) => c.questionId)).toContain('q1')
    expect(due.map((c) => c.questionId)).toContain('q2')
    expect(due.map((c) => c.questionId)).not.toContain('q3')
  })
})

describe('SM-2 getNextReviewLabel', () => {
  it('should return correct labels', () => {
    const card = createCard('q1')

    card.interval = 0
    expect(getNextReviewLabel(card)).toBe('新题')

    card.interval = 1
    expect(getNextReviewLabel(card)).toBe('1天')

    card.interval = 3
    expect(getNextReviewLabel(card)).toBe('3天')

    card.interval = 6
    expect(getNextReviewLabel(card)).toBe('6天')

    card.interval = 14
    expect(getNextReviewLabel(card)).toBe('2周')

    card.interval = 30
    expect(getNextReviewLabel(card)).toBe('1月')

    card.interval = 90
    expect(getNextReviewLabel(card)).toBe('3月')
  })
})
