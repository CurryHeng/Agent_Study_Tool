# Agent 题库 — AI Agent 知识学习平台

基于 SM-2 间隔重复算法的 AI Agent 知识复习工具，内容来自《深入理解 AI Agent：设计原理与工程实践》。

## 快速开始

```bash
npm install
cd server && npm install && cd ..
npm start
```

或双击 `start.bat`，浏览器自动打开 `http://localhost:5173`。

## 功能

### 刷题系统
- **三种模式**：宽松（自由练习）/ 普通（逐题计时评分）/ 严格（模拟考试）
- **SM-2 间隔重复**：根据记忆曲线自动调度复习
- **自选题目**：按章节、收藏夹、自定义选择

### 题库管理
- 填空、单选、多选三种题型，按章节浏览
- 手动添加/编辑题目，一键导出 PDF

### 错题本
- 错题自动收集，标注错因，按章节/错因筛选
- 错题导出 PDF（打印版）

### 思维导图
- 第1章 Agent 概述 + 第2章 上下文工程，设置页面直达

### 学习统计
- 掌握率、正确率、复习日志时间线

### 云同步（可选）
- 注册登录后数据云端存储，多设备同步

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | React 19 + TypeScript + Vite + Tailwind CSS + Zustand |
| 后端 | Express + TypeScript + Drizzle ORM + SQLite |
| 认证 | JWT + refresh token |
| 算法 | SM-2 间隔重复 |

## 项目结构

```
agent-quiz/
├── src/                  # 前端源码
│   ├── components/       # React 组件
│   ├── data/questions.json  # 题库
│   └── lib/              # SM-2 / Schema / Store
├── server/src/           # 后端源码
├── public/               # 静态资源 + 思维导图
├── scripts/start.js      # 一键启动脚本
├── start.bat             # Windows 启动
├── 项目规划报告.md        # 完整规划
└── README.md
```

## 端口

前端 `:5173`，后端 `:3002`。冲突时自动清理。
