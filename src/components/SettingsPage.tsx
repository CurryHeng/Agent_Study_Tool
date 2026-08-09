import { useState, useEffect } from 'react'
import { Trash2, Download, Upload, AlertTriangle, Plus, RefreshCw, Cloud, CloudOff, FileText } from 'lucide-react'
import { loadCards, saveCards, loadLogs, loadWorkbooks, addWorkbook, addWorkbookRemote, syncAll, DEFAULT_WORKBOOK_ID } from '../lib/storage'
import type { Workbook } from '../types'
import { createCard } from '../lib/sm2'
import questionsData from '../data/questions.json'
import { isAuthenticated, getStoredUser } from '../api/client'

export default function SettingsPage() {
  const [message, setMessage] = useState<string | null>(null)
  const [confirmReset, setConfirmReset] = useState(false)
  const [syncing, setSyncing] = useState(false)

  // Workbook management
  const [workbooks, setWorkbooks] = useState<Workbook[]>([])
  const [newWbName, setNewWbName] = useState('')
  const [newWbDesc, setNewWbDesc] = useState('')
  const [showNewWb, setShowNewWb] = useState(false)

  const loggedIn = isAuthenticated()
  const user = getStoredUser()

  useEffect(() => {
    setWorkbooks(loadWorkbooks())
  }, [])

  const showMsg = (msg: string) => {
    setMessage(msg)
    setTimeout(() => setMessage(null), 3000)
  }

  const handleSync = async () => {
    setSyncing(true)
    try {
      const result = await syncAll()
      if (result.success) {
        showMsg(`同步完成，上传了 ${result.uploaded} 条数据`)
      } else {
        showMsg('同步失败，请确认已登录且网络正常')
      }
    } catch {
      showMsg('同步失败')
    } finally {
      setSyncing(false)
    }
  }

  const handleCreateWorkbook = () => {
    if (!newWbName.trim()) return
    addWorkbook(newWbName.trim(), newWbDesc.trim() || undefined)
    addWorkbookRemote(newWbName.trim(), newWbDesc.trim() || undefined)
    setWorkbooks(loadWorkbooks())
    setShowNewWb(false)
    setNewWbName('')
    setNewWbDesc('')
    showMsg('练习册已创建')
  }

  const handleReset = () => {
    if (!confirmReset) {
      setConfirmReset(true)
      return
    }
    const cards = questionsData.map((q) => createCard(q.id))
    saveCards(cards)
    localStorage.removeItem('quiz-app-logs')
    setMessage('已重置所有复习进度')
    setConfirmReset(false)
    setTimeout(() => setMessage(null), 3000)
  }

  const handleExport = () => {
    const data = {
      cards: loadCards(),
      logs: loadLogs(),
      exportedAt: new Date().toISOString(),
    }
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `记忆题库-备份-${new Date().toISOString().split('T')[0]}.json`
    a.click()
    URL.revokeObjectURL(url)
    setMessage('导出成功')
    setTimeout(() => setMessage(null), 3000)
  }

  const handleImport = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.json'
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0]
      if (!file) return
      const reader = new FileReader()
      reader.onload = () => {
        try {
          const data = JSON.parse(reader.result as string)
          if (data.cards && Array.isArray(data.cards)) {
            saveCards(data.cards)
            if (data.logs) {
              localStorage.setItem('quiz-app-logs', JSON.stringify(data.logs))
            }
            setMessage(`导入成功：${data.cards.length} 张卡片`)
            setTimeout(() => setMessage(null), 3000)
            window.location.reload()
          } else {
            setMessage('无效的备份文件')
            setTimeout(() => setMessage(null), 3000)
          }
        } catch {
          setMessage('文件解析失败')
          setTimeout(() => setMessage(null), 3000)
        }
      }
      reader.readAsText(file)
    }
    input.click()
  }

  return (
    <div className="space-y-5 animate-fade-in">
      <h1 className="text-xl font-bold text-slate-800">设置</h1>

      {message && (
        <div className="px-4 py-2.5 bg-emerald-50 text-emerald-700 rounded-xl text-sm font-medium animate-slide-up">
          {message}
        </div>
      )}

      {/* Account status */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {loggedIn ? <Cloud size={18} className="text-green-500" /> : <CloudOff size={18} className="text-slate-400" />}
            <div>
              <p className="text-sm font-medium text-slate-700">
                {loggedIn ? `已登录：${user?.username}` : '未登录'}
              </p>
              <p className="text-xs text-slate-400">
                {loggedIn ? '数据自动同步到云端，多设备共享' : '数据仅存储在浏览器本地'}
              </p>
            </div>
          </div>
          {loggedIn && (
            <button
              onClick={handleSync}
              disabled={syncing}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-emerald-600 bg-emerald-50 rounded-lg hover:bg-emerald-100 transition-all border border-emerald-200 disabled:opacity-50"
            >
              <RefreshCw size={13} className={syncing ? 'animate-spin' : ''} />
              立即同步
            </button>
          )}
        </div>
      </div>

      {/* 思维导图 */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm divide-y divide-slate-100">
        <div className="px-5 py-4">
          <h3 className="font-semibold text-sm text-slate-800 flex items-center gap-2">
            <FileText size={15} className="text-emerald-500" />
            思维导图
          </h3>
          <p className="text-xs text-slate-400 mt-1">AI Agent 知识思维导图，新窗口打开</p>
        </div>

        <a href="/Agent-第1章-思维导图.html" target="_blank" rel="noopener noreferrer"
          className="px-5 py-3 flex items-center justify-between hover:bg-slate-50 transition-colors cursor-pointer no-underline text-inherit block">
          <div className="flex items-center gap-3">
            <FileText size={17} className="text-blue-500" />
            <div>
              <p className="text-sm text-slate-700">第1章：AI Agent 概述</p>
              <p className="text-xs text-slate-400">核心公式 · React循环 · Harness工程 · 编排模式 · 护栏</p>
            </div>
          </div>
        </a>
        <a href="/Agent-第2章-思维导图.html" target="_blank" rel="noopener noreferrer"
          className="px-5 py-3 flex items-center justify-between hover:bg-slate-50 transition-colors cursor-pointer no-underline text-inherit block">
          <div className="flex items-center gap-3">
            <FileText size={17} className="text-purple-500" />
            <div>
              <p className="text-sm text-slate-700">第2章：上下文工程</p>
              <p className="text-xs text-slate-400">KV Cache · 注意力机制 · 提示工程 · Agent Skills · 上下文压缩</p>
            </div>
          </div>
        </a>
      </div>

      {/* Data management */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm divide-y divide-slate-100">
        <div className="px-5 py-4">
          <h3 className="font-semibold text-sm text-slate-800">数据管理</h3>
          <p className="text-xs text-slate-400 mt-1">导出或导入你的复习数据</p>
        </div>
        <div className="px-5 py-3 flex items-center justify-between hover:bg-slate-50 transition-colors cursor-pointer" onClick={handleExport}>
          <div className="flex items-center gap-3">
            <Download size={17} className="text-green-500" />
            <div>
              <p className="text-sm text-slate-700">导出备份</p>
              <p className="text-xs text-slate-400">下载复习进度和日志</p>
            </div>
          </div>
        </div>
        <div className="px-5 py-3 flex items-center justify-between hover:bg-slate-50 transition-colors cursor-pointer" onClick={handleImport}>
          <div className="flex items-center gap-3">
            <Upload size={17} className="text-blue-500" />
            <div>
              <p className="text-sm text-slate-700">导入备份</p>
              <p className="text-xs text-slate-400">从备份文件恢复数据</p>
            </div>
          </div>
        </div>
      </div>

      {/* Workbook management */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm divide-y divide-slate-100">
        <div className="px-5 py-4 flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-sm text-slate-800">练习册管理</h3>
            <p className="text-xs text-slate-400 mt-1">管理你的练习册，每道题目归属于一个练习册</p>
          </div>
          <button onClick={() => setShowNewWb(!showNewWb)}
            className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-emerald-600 bg-emerald-50 rounded-lg hover:bg-emerald-100 transition-all border border-emerald-200">
            <Plus size={13} /> 新建
          </button>
        </div>

        {showNewWb && (
          <div className="px-5 py-4 bg-slate-50 animate-slide-up space-y-3">
            <input value={newWbName} onChange={(e) => setNewWbName(e.target.value)}
              placeholder="练习册名称"
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400" />
            <input value={newWbDesc} onChange={(e) => setNewWbDesc(e.target.value)}
              placeholder="描述（可选）"
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400" />
            <div className="flex gap-2">
              <button onClick={handleCreateWorkbook}
                className="px-4 py-1.5 text-xs font-medium text-white bg-emerald-600 rounded-lg hover:bg-emerald-700 transition-all">
                创建
              </button>
              <button onClick={() => { setShowNewWb(false); setNewWbName(''); setNewWbDesc('') }}
                className="px-4 py-1.5 text-xs text-slate-500 hover:text-slate-700 transition-colors">
                取消
              </button>
            </div>
          </div>
        )}

        {workbooks.map((wb) => (
          <div key={wb.id} className="px-5 py-3 flex items-center justify-between hover:bg-slate-50 transition-colors">
            <div>
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium text-slate-700">{wb.name}</p>
                {wb.id === DEFAULT_WORKBOOK_ID && (
                  <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-500">默认</span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                {wb.description || '无描述'} · 创建于 {wb.createdAt}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Danger zone */}
      <div className="bg-white rounded-xl border border-red-200 shadow-sm">
        <div className="px-5 py-4">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle size={15} className="text-red-500" />
            <h3 className="font-semibold text-sm text-red-700">危险操作</h3>
          </div>
          <p className="text-xs text-slate-400">重置后将清除所有复习进度，题目数据不受影响</p>
        </div>
        <div className="px-5 py-3 border-t border-red-100">
          <button
            onClick={handleReset}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              confirmReset
                ? 'bg-red-600 text-white hover:bg-red-700'
                : 'text-red-600 hover:bg-red-50 border border-red-200'
            }`}
          >
            <Trash2 size={15} />
            {confirmReset ? '确认重置？点击再次确认' : '重置所有复习进度'}
          </button>
          {confirmReset && (
            <button
              onClick={() => setConfirmReset(false)}
              className="ml-3 px-4 py-2 text-sm text-slate-500 hover:text-slate-700 transition-colors"
            >
              取消
            </button>
          )}
        </div>
      </div>

      {/* About */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
        <h3 className="font-semibold text-sm text-slate-800 mb-2">关于</h3>
        <p className="text-xs text-slate-400 leading-relaxed">
          Agent 题库 — 基于 SM-2 间隔重复算法的 AI Agent 知识点复习工具。
          内容来源：《深入理解 AI Agent：设计原理与工程实践》第1-2章。
          {loggedIn ? '数据云端存储，多设备自动同步。' : '数据存储在浏览器本地。登录后可开启云端同步。'}
        </p>
      </div>
    </div>
  )
}
