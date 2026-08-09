import { execSync, spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const root = join(__dirname, '..')

const SERVER_PORT = 3002
const VITE_PORT = 5173
const VITE_URL = `http://localhost:${VITE_PORT}`
const HEALTH_URL = `http://localhost:${SERVER_PORT}/api/health`

function killPort(port) {
  try {
    if (process.platform === 'win32') {
      execSync(`netstat -ano | findstr :${port} | findstr LISTENING`, { encoding: 'utf8', stdio: 'pipe' })
        .trim().split('\n').filter(Boolean).forEach(line => {
          const pid = line.trim().split(/\s+/).pop()
          if (pid && pid !== '0') {
            try { execSync(`taskkill /F /PID ${pid}`, { stdio: 'pipe' }) } catch {}
          }
        })
    } else {
      execSync(`lsof -ti:${port} | xargs kill -9 2>/dev/null`, { stdio: 'pipe' })
    }
  } catch {}
}

// Kill old processes on both ports
console.log('🔧 清理端口...')
killPort(SERVER_PORT)
killPort(VITE_PORT)

// Wait a moment for ports to release
await new Promise(r => setTimeout(r, 1500))

// Start backend
console.log(`🔧 启动后端 (端口 ${SERVER_PORT})...`)
const server = spawn('npx', ['tsx', 'src/index.ts'], {
  cwd: join(root, 'server'),
  stdio: 'pipe',
  shell: true,
  env: { ...process.env, FORCE_COLOR: '1' },
})

server.stdout.on('data', (d) => process.stdout.write(`[后端] ${d}`))
server.stderr.on('data', (d) => process.stderr.write(`[后端] ${d}`))

// Wait for server to be ready
for (let i = 0; i < 30; i++) {
  await new Promise(r => setTimeout(r, 1000))
  try {
    const resp = await fetch(HEALTH_URL)
    if (resp.ok) {
      console.log('✅ 后端就绪')
      break
    }
  } catch {}
  if (i === 29) console.log('⚠️  后端启动超时，继续...')
}

// Start frontend
console.log(`🔧 启动前端 (端口 ${VITE_PORT})...`)
const vite = spawn('npx', ['vite', '--host', '--strictPort'], {
  cwd: root,
  stdio: 'pipe',
  shell: true,
  env: { ...process.env, FORCE_COLOR: '1' },
})

vite.stdout.on('data', (d) => process.stdout.write(`[前端] ${d}`))
vite.stderr.on('data', (d) => process.stderr.write(`[前端] ${d}`))

// Wait for Vite
await new Promise(r => setTimeout(r, 2000))

// Open browser
console.log(`\n🌐 打开浏览器: ${VITE_URL}`)
if (process.platform === 'win32') {
  execSync(`start ${VITE_URL}`, { stdio: 'pipe' })
} else if (process.platform === 'darwin') {
  execSync(`open ${VITE_URL}`, { stdio: 'pipe' })
} else {
  execSync(`xdg-open ${VITE_URL}`, { stdio: 'pipe' })
}

console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
console.log('  StudyForge 已启动!')
console.log(`  前端: ${VITE_URL}`)
console.log(`  后端: http://localhost:${SERVER_PORT}`)
console.log('  按 Ctrl+C 停止所有服务')
console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\n🛑 正在停止...')
  server.kill()
  vite.kill()
  process.exit(0)
})
