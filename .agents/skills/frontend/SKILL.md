---
name: frontend
description: EStudy 前端（Vue 3）开发规范。当编写或修改 frontend/ 下的 Vue 组件、页面、Pinia store、路由、API 请求层时加载。
---

# frontend — Vue 3 前端开发规范

## 用途
指导 Vue 3 前端的开发，复用现有 React 项目的交互设计与页面结构，迁移到 Vue 组合式 API。

## 何时加载
- 编写/修改 `frontend/src/**` 下的组件、页面、store、router、api client
- 涉及刷题、题库、错题本、思维导图、设置等页面时

## 必须遵守的规范

### 1. 技术栈（已确定）
- Vue 3 + Vite + TypeScript
- 状态管理：Pinia
- 路由：Vue Router
- 样式：Tailwind CSS（v3，`src/style.css` 已定义 `.card/.btn-primary/.btn-ghost/.input` 组件类）
- 数学公式：KaTeX；思维导图：`markmap-lib` + `markmap-view`（`src/components/MindMap.vue`）

### 1.1 视觉设计原则（参考 Anthropic 官方 frontend-design / theme-factory skill，只学原则）
- **主题源于内容**：配色/字体/布局从"学习/刷题"这个主题出发，不套通用模板。当前品牌基调：indigo→purple 渐变 + emerald 强调，与旧 React 一致。
- **克制**：把"记忆点"留给一个地方（如 hero 渐变卡片），其余保持克制、留白充足。
- **字词即设计**：按钮用主动动词（"开始刷题""保存"，不用"提交"）；空状态是行动邀请（"暂无错题，去刷题吧"）；错误说明要具体、不道歉。
- **一致性**：同一操作全程同名（如"登录"按钮→"已登录"提示）。
- 复用 Tailwind 语义色（slate/indigo/emerald/red/orange），不硬编码 hex。

### 1.2 内置题库约定
- 系统内置题库固定 `workbook_id = 0`（见 `src/lib/constants.ts` 的 `SYSTEM_WORKBOOK_ID`）。
- 各列表页（题库/思维导图）必须把"内置题库"作为选项之一（只读，用户不能增删改）。

### 2. 页面结构（对照现有 React 页面迁移）
| 现有 React 页面 | Vue 目标 |
|---|---|
| Dashboard.tsx | 首页 / 复习入口 |
| QuizSession.tsx / StrictSession.tsx | 刷题（宽松/普通/严格三模式）|
| QuestionList.tsx / AddQuestion.tsx | 题库 + 添加题目 |
| QuestionCard.tsx / RatingButtons.tsx / QuestionTimer.tsx | 题目卡片组件 |
| Stats.tsx | 学习统计 |
| SettingsPage.tsx | 设置 + 思维导图 + 数据管理 |
| LoginPage / RegisterPage | 登录 / 注册 |

### 3. 编码约定
- 使用 `<script setup lang="ts">` 组合式 API。
- 复用现有交互设计（三模式刷题、错题档案、错题对比 UI），不要丢失功能。
- API 请求统一走封装的 client（JWT + 401 自动 refresh 重试，参考现有 `src/api/client.ts` 逻辑）。
- 判题逻辑：选择题程序判题、填空题/简答题人工评分（again/hard/good/easy），逻辑与现有保持一致。

### 4. 数据模型
- 前端类型对齐 docs 混合模型：标准题库字段（type/content/options/answer/analysis/knowledge_id/difficulty）+ 错题/学习过程字段（wrong_answer/wrong_reason/steps/summary）。

### 参考代码
- 现有 React 前端：`src/components/*.tsx`、`src/lib/*.ts`、`src/api/client.ts`（交互与逻辑蓝本）。
