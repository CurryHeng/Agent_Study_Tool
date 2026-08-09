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

const markdownPath = path.resolve(__dirname, '../../1000题 高数错题集.md')
const outputPath = path.resolve(__dirname, '../src/data/questions.json')

function parseMarkdown(content: string): Question[] {
  const lines = content.split('\n')
  const questions: Question[] = []

  let currentChapter = ''
  let i = 0

  while (i < lines.length) {
    const line = lines[i]

    // Chapter header: ## 📘 第一章：函数极限与连续
    const chapterMatch = line.match(/^##\s+(.+)/)
    if (chapterMatch) {
      // Strip leading emoji/icon + whitespace, fix any broken surrogate pairs
      currentChapter = chapterMatch[1]
        .replace(/[\uD800-\uDFFF]/g, '')
        .replace(/^[^\w一-鿿]+\s*/, '')
        .trim()
      i++
      continue
    }

    // Question header: ### ❌ 错题 1.1（原第 2 题）
    const qMatch = line.match(
      /^### (?:❌ 错题 )?(\d+(?:\.\d+)?)\s*[（(]\s*原(?:第|大题第)\s*(\d+)\s*题?\s*[）)]/
    )
    if (qMatch) {
      const questionNumber = qMatch[1]
      const originalNumber = qMatch[2]
      i++

      // Skip blank lines
      while (i < lines.length && lines[i].trim() === '') i++

      // Collect problem lines ("> " prefix)
      let problem = ''
      while (i < lines.length && lines[i].startsWith('> ')) {
        problem += lines[i].replace(/^>\s*/, '') + '\n'
        i++
      }

      // Parse sections — look for **【marker】**
      let wrongAnswer = ''
      let wrongReason = ''
      let correctAnswer = ''
      let steps = ''
      let summary = ''
      let currentSection = ''

      while (i < lines.length) {
        const trimmed = lines[i].trim()

        // Stop at next question or chapter
        if (/^### (?:❌ 错题 )?\d/.test(trimmed) || trimmed.startsWith('## ')) break
        // Stop at separator
        if (trimmed === '---') { i++; break }

        if (trimmed === '**【错误档案】**') { currentSection = 'wrong'; i++; continue }
        if (trimmed === '**【正确解析】**') { currentSection = 'correct'; i++; continue }
        if (trimmed === '**【一句话总结】**') { currentSection = 'summary'; i++; continue }

        if (currentSection === 'wrong') {
          const wa = trimmed.match(/^\*\*错误答案[：:]\*\*\s*(.*)/)
          const wr = trimmed.match(/^\*\*错误原因[：:]\*\*\s*(.*)/)
          if (wa) wrongAnswer = wa[1].trim()
          else if (wr) wrongReason = wr[1].trim()
        } else if (currentSection === 'correct') {
          const ca = trimmed.match(/^\*\*正确答案[：:]\*\*\s*(.*)/)
          const cs = trimmed.match(/^\*\*核心步骤[：:]\*\*\s*(.*)/)
          if (ca) correctAnswer = ca[1].trim()
          else if (cs) {
            steps = cs[1].trim()
            // Collect following lines as extended steps
            let j = i + 1
            while (j < lines.length &&
              !lines[j].trim().startsWith('**【') &&
              !/^### (?:❌ 错题 )?\d/.test(lines[j].trim()) &&
              !lines[j].trim().startsWith('## ') &&
              lines[j].trim() !== '---') {
              const sl = lines[j].trim()
              if (sl) steps += '\n' + sl
              j++
            }
            i = j - 1
          }
        } else if (currentSection === 'summary') {
          if (trimmed && !trimmed.startsWith('**【') && trimmed !== '---') {
            if (summary) summary += ' ' + trimmed
            else summary = trimmed
          }
        }

        i++
      }

      const id = `q-${questionNumber.replace(/\./g, '-')}`

      questions.push({
        id,
        chapter: currentChapter,
        questionNumber,
        originalNumber,
        problem: problem.trim(),
        wrongAnswer: wrongAnswer || '（无）',
        wrongReason: wrongReason || '（未记录）',
        correctAnswer: correctAnswer || '（见步骤）',
        steps: steps.trim(),
        summary: summary || '（无总结）',
        knowledgePoints: [],
      })

      continue
    }

    i++
  }

  return questions
}

function generateKnowledgePoints(questions: Question[]): void {
  // Extract knowledge points from chapter + summary keywords
  const keywordMap: Record<string, string[]> = {
    '反函数': ['反函数'],
    '分段': ['分段函数'],
    '递推': ['递推函数'],
    '无穷小': ['无穷小比较'],
    '夹逼': ['夹逼定理'],
    '单调有界': ['单调有界准则'],
    '极限': ['极限计算'],
    '导数': ['导数定义'],
    '可导': ['可导性'],
    '连续': ['连续性'],
    '微分': ['微分概念'],
    '积分': ['积分计算'],
    '不定积分': ['不定积分'],
    '定积分': ['定积分'],
    '反常积分': ['反常积分'],
    '瑕积分': ['瑕积分'],
    '原函数': ['原函数'],
    '换元': ['换元积分法'],
    '分部积分': ['分部积分法'],
    '泰勒': ['泰勒展开'],
    '麦克劳林': ['麦克劳林展开'],
    '洛必达': ['洛必达法则'],
    '拉格朗日': ['拉格朗日中值定理'],
    '中值定理': ['中值定理'],
    '华里士': ['华里士公式'],
    '万能代换': ['万能代换'],
    '三角代换': ['三角代换'],
    '参数方程': ['参数方程'],
    '绝对值': ['绝对值处理'],
    '奇函数': ['奇偶性'],
    '偶函数': ['奇偶性'],
    '奇偶': ['奇偶性'],
    '压缩映像': ['压缩映像原理'],
    '数列': ['数列极限'],
    '函数极限': ['函数极限'],
    '收敛': ['收敛性判别'],
    '发散': ['发散'],
    '连续函数': ['连续函数性质'],
    '变限积分': ['变限积分'],
  }

  for (const q of questions) {
    const kps = new Set<string>()
    // Add chapter-based knowledge point
    const ch = q.chapter
    if (ch.includes('极限')) kps.add('极限')
    if (ch.includes('连续')) kps.add('连续性')
    if (ch.includes('微分')) kps.add('微分')
    if (ch.includes('积分')) kps.add('积分')

    // Scan summary and steps for keywords
    const text = q.summary + ' ' + q.steps
    for (const [kw, kpList] of Object.entries(keywordMap)) {
      if (text.includes(kw)) {
        for (const kp of kpList) kps.add(kp)
      }
    }

    q.knowledgePoints = [...kps].slice(0, 6)
  }
}

// Load existing knowledge points before regenerating
let existingKPs = new Map<string, string[]>()
try {
  const existing = JSON.parse(fs.readFileSync(outputPath, 'utf-8')) as Question[]
  for (const q of existing) {
    if (q.knowledgePoints && q.knowledgePoints.length > 0) {
      existingKPs.set(q.id, q.knowledgePoints)
    }
  }
} catch {
  // No existing file
}

const content = fs.readFileSync(markdownPath, 'utf-8')
const questions = parseMarkdown(content)

// Apply knowledge points: prefer existing, auto-generate for new questions
for (const q of questions) {
  const prev = existingKPs.get(q.id)
  if (prev) {
    q.knowledgePoints = prev
  }
}
// Auto-generate for questions without existing KPs
generateKnowledgePoints(questions.filter((q) => q.knowledgePoints.length === 0))

fs.writeFileSync(outputPath, JSON.stringify(questions, null, 2), 'utf-8')
console.log(`Parsed ${questions.length} questions.\n`)
questions.forEach((q) => {
  const kps = q.knowledgePoints.length > 0 ? ` [${q.knowledgePoints.join(', ')}]` : ''
  console.log(`  ${q.id}: ${q.chapter} - 错题 ${q.questionNumber} (原第${q.originalNumber}题)${kps}`)
})
