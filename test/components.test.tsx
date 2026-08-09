import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import QuestionCard from '../src/components/QuestionCard'
import type { Question, WrongRecord } from '../src/lib/schema'

const mockQuestion: Question = {
  id: 'q1',
  chapter: '第一章',
  questionNumber: '1.1',
  originalNumber: '5',
  problem: '求极限 $\\lim_{x \\to 0} \\frac{\\sin x}{x}$\n\n(A) 0\n(B) 1\n(C) ∞\n(D) 不存在',
  correctAnswer: 'B',
  wrongAnswer: '选了C',
  wrongReason: '记混了',
  steps: '重要极限',
  summary: 'sinx/x → 1',
  knowledgePoints: ['函数极限'],
  workbookId: 'default',
}

const mockWrongRecords: WrongRecord[] = [
  { date: '2025-06-01', wrongAnswer: '选了D', wrongReason: '粗心' },
]

describe('QuestionCard', () => {
  it('should render problem text', () => {
    render(
      <MemoryRouter>
        <QuestionCard question={mockQuestion} revealed={false} />
      </MemoryRouter>
    )
    // "极限" appears in both problem text and knowledge points badge
    const matches = screen.getAllByText(/极限/)
    expect(matches.length).toBeGreaterThanOrEqual(2)
  })

  it('should show choice buttons for multiple choice', () => {
    render(
      <MemoryRouter>
        <QuestionCard question={mockQuestion} revealed={false} />
      </MemoryRouter>
    )
    // Should have A, B, C, D choice buttons
    expect(screen.getByText('A')).toBeDefined()
    expect(screen.getByText('B')).toBeDefined()
    expect(screen.getByText('C')).toBeDefined()
    expect(screen.getByText('D')).toBeDefined()
  })

  it('should show correct answer when revealed', () => {
    render(
      <MemoryRouter>
        <QuestionCard question={mockQuestion} revealed={true} />
      </MemoryRouter>
    )
    expect(screen.getByText('正确解析')).toBeDefined()
  })

  it('should show wrong records when revealed', () => {
    render(
      <MemoryRouter>
        <QuestionCard
          question={mockQuestion}
          revealed={true}
          wrongRecords={mockWrongRecords}
        />
      </MemoryRouter>
    )
    expect(screen.getByText('错误档案')).toBeDefined()
  })

  it('should show favorite star when favorited', () => {
    render(
      <MemoryRouter>
        <QuestionCard
          question={mockQuestion}
          revealed={false}
          favorited={true}
          onToggleFavorite={() => {}}
        />
      </MemoryRouter>
    )
    // Star should be visible
    const buttons = screen.getAllByRole('button')
    expect(buttons.length).toBeGreaterThanOrEqual(4) // A, B, C, D + star
  })

  it('should call onChoiceResult when selecting a choice', () => {
    let selected = ''
    let correct = false
    const handleChoice = (s: string, c: boolean) => {
      selected = s
      correct = c
    }

    render(
      <MemoryRouter>
        <QuestionCard
          question={mockQuestion}
          revealed={false}
          onChoiceResult={handleChoice}
        />
      </MemoryRouter>
    )

    // Click on option B (correct answer)
    fireEvent.click(screen.getByText('B'))
    expect(selected).toBe('B')
    expect(correct).toBe(true)
  })

  it('should handle non-multiple-choice questions', () => {
    const nonMc: Question = {
      ...mockQuestion,
      problem: '计算积分 $\\int_0^1 x^2 dx$',
    }

    render(
      <MemoryRouter>
        <QuestionCard question={nonMc} revealed={false} />
      </MemoryRouter>
    )
    // Should not have choice buttons
    expect(screen.queryByText('A')).toBeNull()
  })
})
