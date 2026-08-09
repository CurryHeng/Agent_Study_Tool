import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

interface Question {
  id: string
  chapter: string
  questionNumber: string
  originalNumber: string
  problem: string
  wrongAnswer: string
  wrongReason: string
  correctAnswer: string
  steps: string
  summary: string
  knowledgePoints: string[]
}

const questionsPath = path.resolve(__dirname, '../src/data/questions.json')
const outputPath = path.resolve(__dirname, '../../1000题 高数错题集.md')

const questions: Question[] = JSON.parse(fs.readFileSync(questionsPath, 'utf-8'))

// Group by chapter
const chapterOrder: string[] = []
const chapterMap = new Map<string, Question[]>()
for (const q of questions) {
  if (!chapterMap.has(q.chapter)) {
    chapterMap.set(q.chapter, [])
    chapterOrder.push(q.chapter)
  }
  chapterMap.get(q.chapter)!.push(q)
}

const lines: string[] = []
const chEmojis: Record<string, string> = {
  '第一章：函数极限与连续': '📘',
  '第二章：数列极限': '📙',
  '第三章：一元函数微分学的概念': '📘',
  '第四章：一元函数微分学的计算': '📘',
  '第八章：一元函数积分学的概念与性质': '📘',
  '第九章：一元函数积分学的计算': '📘',
}

for (const chapter of chapterOrder) {
  const emoji = chEmojis[chapter] || '📘'
  lines.push(`## ${emoji} ${chapter}`)
  lines.push('')

  const chQuestions = chapterMap.get(chapter)!
  for (const q of chQuestions) {
    const qNum = q.questionNumber
    const origNum = q.originalNumber
    const title = `### ❌ 错题 ${qNum}（原第 ${origNum} 题）`
    lines.push(title)
    lines.push('')

    // Problem — strip existing "> " prefix, then add fresh one
    const problemLines = q.problem.split('\n')
    for (const raw of problemLines) {
      const pl = raw.replace(/^>\s*/, '')
      lines.push(`> ${pl}`)
    }
    lines.push('')

    // Wrong archive
    lines.push('**【错误档案】**')
    lines.push('')
    lines.push(`**错误答案：** ${q.wrongAnswer}`)
    lines.push('')
    lines.push(`**错误原因：** ${q.wrongReason}`)
    lines.push('')

    // Correct answer
    lines.push('**【正确解析】**')
    lines.push('')
    lines.push(`**正确答案：** ${q.correctAnswer}`)
    lines.push('')

    // Steps (multi-line)
    lines.push(`**核心步骤：** ${q.steps}`)
    lines.push('')

    // Summary
    lines.push('**【一句话总结】**')
    lines.push('')
    lines.push(q.summary)
    lines.push('')

    // Separator
    lines.push('---')
    lines.push('')
  }
}

fs.writeFileSync(outputPath, lines.join('\n'), 'utf-8')
console.log(`Generated ${questions.length} questions in clean format.`)
