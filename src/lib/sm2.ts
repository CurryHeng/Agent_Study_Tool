import type { Rating, ReviewCard } from '../types'

const DEFAULT_EASE = 2.5
const MIN_EASE = 1.3
const EASE_BONUS = 0.15
const EASE_PENALTY = 0.2

function nextDay(date: Date, days: number): string {
  const d = new Date(date)
  d.setDate(d.getDate() + days)
  return d.toISOString().split('T')[0]
}

export function createCard(questionId: string): ReviewCard {
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

export function reviewCard(card: ReviewCard, rating: Rating, isCorrect?: boolean, now: Date = new Date()): ReviewCard {
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

export function getDueCards(cards: ReviewCard[]): ReviewCard[] {
  const today = new Date().toISOString().split('T')[0]
  return cards.filter((c) => c.nextReview <= today)
}

export function getNextReviewLabel(card: ReviewCard): string {
  if (card.interval === 0) return '新题'
  if (card.interval < 1) return '<1天'
  if (card.interval === 1) return '1天'
  if (card.interval < 7) return `${card.interval}天`
  if (card.interval < 30) return `${Math.round(card.interval / 7)}周`
  return `${Math.round(card.interval / 30)}月`
}
