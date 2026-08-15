/**
 * EStudy 前端 E2E 冒烟测试程序
 *
 * 自动拉起后端 + 前端，等待服务就绪后运行 Playwright 测试，结束后清理进程。
 * 用法：npm run test:e2e
 */
import { spawn, execSync } from 'node:child_process'
import { setTimeout as delay } from 'node:timers/promises'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const backendDir = path.resolve(root, '../backend')
const frontendDir = root

function start(desc, command, args, cwd) {
  console.log(`[e2e] 启动 ${desc} ...`)
  const child = spawn(command, args, {
    cwd,
    shell: true,
    stdio: 'pipe',
  })
  child.stdout?.on('data', (d) => process.stdout.write(`[${desc}] ${d}`))
  child.stderr?.on('data', (d) => process.stderr.write(`[${desc}] ${d}`))
  child.on('exit', (code) => console.log(`[e2e] ${desc} 退出 code=${code}`))
  return child
}

function killTree(child) {
  if (!child || child.pid == null) return
  if (process.platform === 'win32') {
    try {
      execSync(`taskkill /F /T /PID ${child.pid}`, { stdio: 'ignore' })
    } catch {
      // already exited
    }
  } else {
    child.kill('SIGTERM')
  }
}

async function waitFor(url, timeoutMs = 120_000) {
  const start = Date.now()
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(url)
      if (res.ok) return true
    } catch {
      // not ready yet
    }
    await delay(1000)
  }
  throw new Error(`等待服务超时: ${url}`)
}

const backend = start('backend', 'conda run -n EStudy python -m uvicorn main:app --port 8080', [], backendDir)
const frontend = start('frontend', 'npm run dev', [], frontendDir)

try {
  await waitFor('http://127.0.0.1:8080/api/health')
  console.log('[e2e] 后端已就绪')
  await waitFor('http://localhost:5175')
  console.log('[e2e] 前端已就绪')

  console.log('[e2e] 运行 Playwright 测试 ...')
  execSync('npx playwright test', { cwd: frontendDir, stdio: 'inherit' })
} finally {
  console.log('[e2e] 清理进程 ...')
  killTree(backend)
  killTree(frontend)
}
