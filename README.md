# EStudy —— 智能题库与学习系统

面向大学生期末复习场景，通过 AI Agent 将课程资料（提纲、课件、教材等）自动转化为结构化学习资源：

> **上传学习资料 → 自动生成知识结构、思维导图、题库 → 刷题与错题记录形成学习闭环。**

统一入口为 **AI 助手**（主 Agent，ReAct）：理解用户意图、编排任务、调用领域专家（知识 / 出题 / 教练）完成工作。

## ✨ 已完成功能

| 模块 | 状态 | 说明 |
|---|---|---|
| 资料导入 | ✅ | PDF / Word / PPT / Markdown / TXT / HTML；图片 OCR（需配置多模态 API） |
| 文档解析 | ✅ | 统一 `parse(file) -> Document`，Parser 与 Agent 解耦 |
| 知识点提取 | ✅ | 规则引擎 + LLM 抽样交叉验证，自动构建知识树 |
| 思维导图 | ✅ | markmap 可视化（已修复渲染 bug） |
| AI 自动出题/审题 | ✅ | 生成 + 三层校验 + Review 回环（≤2 次） |
| 题库管理 | ✅ | CRUD / 软删除 / 收藏 / 搜索 / 举一反三 |
| 刷题 | ✅ | 宽松 / 普通 / 严格三模式 + 判题 + FSRS-6 |
| 错题本 | ✅ | 答错自动收集 / 错因编辑 / 筛选 |
| 学习统计 | ✅ | 掌握度、错因分类、复习历史、**日历式学习活跃热力图** |
| AI 助手聊天页 | ✅ | steps 展示、写操作确认卡片、navigate 跳转、context 注入 |
| AI 供应商设置 | ✅ | 文本 LLM + 多模态视觉，支持 DeepSeek / OpenAI / Qwen / Gemini / Ollama |

## ��� 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3 + TypeScript + Vite + Tailwind 3 + Pinia + vue-router + markmap + KaTeX |
| 后端 | Python 3.11 + FastAPI + SQLAlchemy 2.0 + Alembic |
| Agent 编排 | LangGraph（ReAct 主 Agent + 专家子图） |
| 数据库 | SQLite（业务数据）+ Chroma（RAG 向量检索） |
| 模型 | DeepSeek / OpenAI / Qwen / Gemini / Ollama（文本与多模态均可配置） |
| 认证 | JWT access（15min）+ refresh 轮换（30 天，哈希落库），bcrypt |

## ��� 项目结构

```text
EStudy/
├── 启动.bat                  # 一键启动（后端 8080 + 前端 5175）
├── AGENTS.md                 # AI 编程工具开发规范
├── README.md
├── backend/                  # FastAPI 后端
│   ├── main.py               # 应用入口
│   ├── config.py             # pydantic-settings
│   ├── api/                  # auth / workbooks / questions / knowledge /
│   │                         #   documents / rag / review / agent / wrong_records /
│   │                         #   stats / settings
│   ├── services/             # 业务层 + ai_settings（多供应商配置）
│   ├── repositories/         # 数据访问层
│   ├── models/               # SQLAlchemy 模型（唯一真相源）
│   ├── schemas/              # Pydantic 模型
│   ├── workflow/             # LangGraph（chat / import）
│   ├── rag/                  # chunker / embedding / chroma / retriever
│   ├── parsers/              # pdf / markdown / word / ppt / image
│   ├── alembic/              # 数据库迁移
│   ├── seed/                 # 种子数据
│   ├── tests/                # 后端测试
│   └── data/                 # SQLite + uploads + chroma（不入库）
├── frontend/                 # Vue 3 前端
│   ├── src/
│   │   ├── api/              # fetch 封装 + 分域 API
│   │   ├── stores/           # Pinia
│   │   ├── router/           # 路由 + 登录守卫
│   │   ├── views/            # 页面
│   │   ├── components/       # MindMap / HeatmapCalendar / MarkdownContent 等
│   │   └── __tests__/        # Vitest 单元测试
│   ├── tests/e2e/            # Playwright E2E 冒烟测试
│   └── scripts/run-e2e.mjs   # 自动拉起前后端并跑 E2E
└── docs/                     # 需求/设计/进度文档
```

## ��� 快速开始

前置：conda 环境 `EStudy`（Python 3.11）、Node.js。

```bash
# 方式一：双击 启动.bat（自动起后端 8080 + 前端 5175 并打开浏览器）

# 方式二：手动
cd backend && uvicorn main:app --reload --port 8080
cd frontend && npm install && npm run dev
```

浏览器访问 <http://localhost:5175>（前端已配 Vite 代理，`/api` 自动转发到 8080）。

### 内置数据与测试账号

```bash
cd backend && python -m seed.seed
```

- **内置题库**（系统工作簿 id=0，全员可见只读）：《深入理解 AI Agent》第 1-2 章，22 题 + 15 个知识节点
- **开发者账号**：`dev` / `dev123456`（仅本地测试）

### AI 供应商配置

设置页 → **AI 功能配置** 可配置：

- **文本 API**：DeepSeek / OpenAI / Qwen / Gemini / Ollama
- **多模态 API**：Qwen / OpenAI / Gemini / Ollama（图片 OCR）

保存后写入 `backend/data/ai_settings.json`；未配置时回退到 `backend/.env` 的 `DEEPSEEK_API_KEY` / `QWEN_API_KEY`。

## ��� API 概览

```text
POST /api/auth/register          POST /api/auth/login
POST /api/auth/refresh           POST /api/auth/logout
GET  /api/auth/me
GET/POST /api/workbooks          GET/PUT/DELETE /api/workbooks/{id}
GET  /api/workbooks/{id}/mindmap
GET/POST /api/questions          POST /api/questions/generate
GET/PUT/DELETE /api/questions/{id}
POST /api/questions/{id}/similar  POST /api/questions/{id}/answer
GET  /api/knowledge              GET /api/knowledge/{id}
POST /api/documents/upload       GET /api/documents
GET/DELETE /api/documents/{id}   POST /api/documents/{id}/index
POST /api/rag/retrieve
GET  /api/review/due             POST /api/review/{id}/favorite
POST /api/agent/chat             # AI 助手统一入口
GET/PUT /api/wrong-records       GET /api/stats
GET/PUT /api/settings/ai         # AI 供应商配置
GET  /api/health
```

## ��� 测试

```bash
# 后端：单元/集成测试 + 静态检查
cd backend && python -m pytest && python -m ruff check .

# 前端：单元测试 + 类型检查 + 构建
cd frontend && npm test && npm run build

# 前端 E2E 冒烟测试（自动拉起前后端，跑完自动清理）
cd frontend && npm run test:e2e
```

当前基线：

- 后端：**166** 个测试通过，ruff 通过
- 前端：**10** 个 Vitest 单元测试通过，vue-tsc / vite build 通过
- E2E：**5** 个 Playwright 冒烟测试通过

## ✅ 已完成 Issues

| Issue | 标题 | 说明 |
|---|---|---|
| #33 | AgentChatView：AI 助手聊天页 | steps / proposals / navigate / context 已接入 |
| #44 | 学习热力图 | 知识点掌握度跳转 + GitHub 式日历热力图 |
| #60 | 思维导图显示修复 | markmap 改用 IPureNode，导图可正常渲染 |
| #36 | 接口契约冻结 | 已关闭，契约写入任务分工文档 |

> 其余进行中/未开始：见 `docs/项目进度.md` 与 GitHub Issues。

## ��� 文档

- `docs/（必读）项目需求说明书.md`
- `docs/（必读）总体设计文档.md`
- `docs/（必读）详细设计.md`
- `docs/（必读）Agent架构分析.md`
- `docs/（必读）任务分工.md`
- `docs/项目进度.md`
