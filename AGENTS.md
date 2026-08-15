# AGENTS.md — EStudy 项目开发指南

> 本文件是 AI 编程工具（OpenCode + DeepSeek V4 Pro）在开发本项目时必须遵循的规范。
> 技术方案以 `docs/` 下的需求分析、总体设计、详细设计文档为准，本文件是对其开发约束的浓缩与固化。
> 当前迭代：P1 冲刺，四人分工见 `docs/开发任务分工.md`。

## 1. 项目目标

**EStudy（原名 StudyForge，2026-08-14 正式更名）——智能题库与学习系统。**

面向大学生期末复习场景，通过 AI Agent 将用户已有的课程资料（提纲、课件、教材等）自动转化为结构化学习资源：

> **上传学习资料 → 自动生成知识结构、思维导图、题库 → 刷题与错题记录形成学习闭环。**

P0 核心链路：

```text
资料导入 → 文档解析 → 知识提取 → 思维导图 → RAG → 自动出题 → AI 审题 → 题库 → 刷题 → 错题记录
```

统一入口为 **Navigator Agent**（总导航 Agent），负责理解用户意图并调度专业 Agent。

## 2. 技术栈

| 层 | 技术 |
|---|---|
| 前端 | **Vue 3 + Vite** |
| 后端 | **FastAPI（Python）** |
| Agent 编排 | **LangGraph**（Orchestrator 工作流与状态管理）|
| 业务数据库 | **SQLite**（结构化业务数据）|
| 向量数据库 | **Chroma**（RAG 语义检索）|
| 文本模型 | **DeepSeek-V4**（文本理解 / 知识提取 / 出题 / 审核 / Navigator）|
| 视觉模型 | **千问视觉模型**（图片理解 / OCR / 复杂视觉内容解析）|
| 认证 | JWT（登录注册，access+refresh 双令牌轮换，已在 FastAPI 实现）|

> 注意：旧 React/Express 代码已删除（2026-08-14），业务逻辑（间隔重复、错题归纳、题库结构）均已移植到 FastAPI 后端。架构以 Vue + FastAPI + LangGraph 为准，不得回退。

## 3. 目录结构

依据详细设计 Pt.2 §9，采用前后端分离结构，P0 已全部实现：

```text
EStudy/
├── frontend/                    # Vue 3 前端（P0-9 完成）
│   ├── package.json / vite.config.ts / tsconfig.json / index.html
│   └── src/
│       ├── main.ts / App.vue / style.css / env.d.ts / types.ts
│       ├── api/                 # client.ts（fetch+JWT+401刷新）+ index.ts（分域 API）
│       ├── stores/              # auth.ts（Pinia）
│       ├── router/              # index.ts（登录守卫）
│       ├── components/          # MarkdownContent.vue（消毒渲染）/ MindMap.vue（markmap）
│       ├── views/               # Login/Register/Dashboard/QuestionBank/Review/WrongBook/MindMap
│       └── __tests__/           # auth.spec.ts / grading.spec.ts / markdown.spec.ts
├── backend/                     # FastAPI 后端（P0-1~P0-8 完成）
│   ├── main.py                  # FastAPI 入口 + CORS
│   ├── config.py                # pydantic-settings 读 .env
│   ├── db/                      # base.py(DeclarativeBase) / engine.py / session.py
│   ├── models/                  # 12 个 SQLAlchemy 模型 + enums.py（唯一真相源）
│   ├── repositories/            # 数据访问层
│   ├── services/                # 业务层（fsrs_scheduler/chapter_sort/grading/llm_service/generation/rag/review/...）
│   ├── schemas/                 # Pydantic 请求/响应模型
│   ├── api/                     # auth/workbooks/questions/knowledge/documents/rag/review/agent/wrong_records
│   ├── workflow/                # LangGraph：state.py(TaskState) + graph.py
│   ├── rag/                     # chunker.py / embedding.py / chroma.py / retriever.py
│   ├── parsers/                 # pdf/markdown/word/ppt/image + factory.py
│   ├── alembic/ + alembic.ini   # 数据库迁移
│   ├── seed/                    # 种子脚本（系统账号/工作簿 + 内置参考题）
│   ├── tests/                   # 后端测试（132 用例）
│   └── data/                    # SQLite(quiz-app.db) + uploads/ + chroma/
└── docs/                        # 需求/设计文档（含 新数据模型设计.md）
```

调用方向（严格分层，下层不主动依赖上层）：

```text
API → Service → Repository → Database

API → Agent Service → Navigator → Orchestrator → 专业 Agent → Tools/RAG/LLM → Service → Repository
```

## 4. 核心设计原则（最高优先级）

1. **Agent 与普通业务代码分离**：用户登录、文件上传、PDF 读取、文件存储、数据库存取、权限控制、选择题判题等确定性逻辑用**普通程序**实现；只有文档内容理解、知识点提取、思维导图生成、题目生成、题目审核、任务规划等非确定性任务才交给 Agent。**不要为了“Agent 化”把所有功能都做成 Agent。**
2. **Agent 不直接执行 SQL**：数据库操作必须经过 `Tool → Service → Repository → Database`。
3. **Agent 间通过结构化 State / JSON 传递**，避免依赖自然语言上下文。
4. **LangGraph 负责工作流与状态管理**。
5. **RAG 作为公共能力服务**，不单独设计复杂的 RAG Agent。
6. **Navigator 与 Orchestrator 职责分离**：Navigator 回答“用户想做什么”，Orchestrator 回答“应该怎么完成”，专业 Agent 负责“具体把事情做好”。
7. **P0 优先，P1/P2 预留接口但不阻塞 P0**。
8. **LLM 输出必须经过结构化解析与校验，不能默认可信**。

## 5. Agent 架构

```text
用户 → Navigator Agent → Orchestrator（LangGraph）→ Document / Knowledge / Question Agent → Review Agent → 用户
```

| Agent | 职责 | 不负责 |
|---|---|---|
| Navigator Agent | 理解自然语言意图、提供功能指导、生成结构化任务计划 | PDF 解析、出题、审核、数据库操作 |
| Orchestrator | 任务规划、任务调度、状态控制（LangGraph 实现）| 具体业务执行 |
| Document Agent | 对已解析文档做内容理解、章节识别 | 原始文件上传/存储 |
| Knowledge Agent | 知识点提取、知识层级构建、思维导图数据 | — |
| Question Agent | 根据知识点生成题目 | 审核、入库 |
| Review Agent | 题目质量审核（正确性/答案/选项/知识点匹配/表述/难度）| 重新生成题目 |

## 6. Agent / LangGraph 开发规范

### 6.1 TaskState（统一任务状态）

所有 Agent 围绕统一 `TaskState` 协作。字段（详细设计 Pt.1 §2.2）：

`task_id, user_id, course_id, user_request, intent, task_plan, current_step, document_ids, knowledge_ids, retrieved_context, generated_data, review_result, permission, errors, final_result`

### 6.2 State 使用规则（各 Agent 只能读写自己的职责范围）

- Navigator：读 Request/Knowledge，写 `intent`、`task_plan`
- Orchestrator：读全部，写 `current_step`、`task_plan`
- Document Agent：读 `document_ids`，写 `generated_data`
- Knowledge Agent：读 `generated_data`/RAG，写 `knowledge_ids`、`generated_data`
- Question Agent：读 knowledge/RAG，写 `generated_data`
- Review Agent：读 `generated_data`，写 `review_result`
- RAG Service：读检索参数，写 `retrieved_context`

### 6.3 工作流

LangGraph 主流程：`START → Navigator → Orchestrator → Task Router → 专业 Agent → Review → Result Handler → END`。

- Review 审核 **FAIL 可循环回 Question Agent 重新生成**，**最大重试 2 次**，仍失败则返回异常（避免无限循环）。
- 简单咨询类任务（如“什么是题库”）由 Navigator 直接回答，不调用专业 Agent。

### 6.4 输入输出协议

统一结构化请求/响应（`AgentRequest` / `AgentResponse`），失败带 `error.code / error.message`（如 `LLM_ERROR`）。

### 6.5 题目结构（Question Agent 输出）

P0 已实现**五种题型**：`single_choice` / `multiple_choice` / `true_false` / `fill_blank` / `short_answer`（`models/enums.py` 为唯一真相源）。统一字段：`type, content, options[], answer, analysis, knowledge_id, difficulty`。简答题已支持 LLM 判分（LLM 不可用时降级用户自评）。

### 6.6 LLM 调用规范

- 统一通过 `LLMService` 封装，Agent **不直接调用模型 SDK**，便于换模型不改 Agent。
- 长文档先 `Chunk → 检索 → 只把相关内容交给 LLM`，**禁止把整个文档直接塞给 LLM**。
- 所有重要 Agent 输出必须经过**三层校验**后才入库：
  1. 格式校验（是否合法 JSON）
  2. 结构校验（必需字段是否存在）
  3. 业务校验（如：选项数=4、答案对应选项、`knowledge_id` 有效、`difficulty` 范围正确）

### 6.7 权限设计

Agent 默认 `read + create`；`update` / `delete` / 批量操作需额外授权。禁止 `LLM → 任意 SQL / 任意文件系统操作 / 任意系统命令`。

## 7. 数据库规范

### 7.1 分工

- **SQLite**：结构化业务数据。
- **Chroma**：语义检索向量数据。

### 7.2 表结构（已按 P0-1-A 设计文档实现，最终以 `docs/新数据模型设计.md` 为准）

`users, workbooks, knowledge, questions, question_options, review_cards, answer_records, wrong_records, documents, agent_tasks, api_keys, refresh_tokens`

- **题目本身**（Question / QuestionOption）与**用户学习记录**（ReviewCard / AnswerRecord / WrongRecord）彻底分离。
- 正确答案唯一事实源是 `Question.answer`；`QuestionOption` 只存内容，不加 `is_correct`。
- `questions.deleted_at` 软删除；`answer_records` / `wrong_records` 对 question 为 **RESTRICT**（历史/反思不可静默丢失）。
- 删除行为：组合关系（option / review_card）CASCADE；知识父节点、knowledge_id 用 SET NULL。
- 预留系统账号 `id=0` + 系统工作簿 `id=0`（内置题库）。
- `documents.status`：`pending / processing / success / failed`；`agent_tasks.status`：`pending / running / success / failed / cancelled`。

## 8. API 开发规范

REST 风格，路由前缀 `/api`。**实际路由以下为准（与 openapi.json 核对，2026-08-14）**：

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
GET/PUT /api/wrong-records...    GET /api/stats
GET  /api/health
```

> 注意：早期文档中的 `/api/courses`、`/api/exams/*` 已废弃；练习册概念为 **workbook**，答题入口为 `POST /api/questions/{id}/answer`。上传文档后会**自动构建向量索引**（2026-08-14 修复，此前需手动 `/index`）。

## 9. 开发与运行命令

### 9.1 配置（.env）

配置项由 `config.py` 统一读取，不硬编码 API Key（详细设计 Pt.3 §18）：

```text
DEEPSEEK_API_KEY=  QWEN_API_KEY=  LLM_MODEL=  EMBEDDING_MODEL=
DATABASE_URL=  CHROMA_PATH=  MAX_FILE_SIZE=  MAX_RETRY=
JWT_SECRET=  ENCRYPTION_KEY=
```

### 9.2 命令

```bash
# 后端（FastAPI）
cd backend
pip install -r requirements.txt          # 安装依赖（首次）
uvicorn main:app --reload                # 启动开发服务（端口 8080，与 vite 代理/启动.bat 一致）

# 数据库迁移（Alembic）
cd backend
python -m alembic revision --autogenerate -m "描述"   # 生成迁移
python -m alembic upgrade head                        # 应用迁移建表

# 种子数据（系统账号/工作簿 + 内置参考题）
cd backend
python -m seed.seed

# 后端测试
cd backend
python -m pytest
python -m ruff check .                    # 静态检查

# 前端（Vue 3 + Vite）
cd frontend
npm install                              # 安装依赖（首次）
npm run dev                              # 启动开发服务（端口 5175）
npm run typecheck                        # vue-tsc 类型检查
npm run build                            # 类型检查 + 生产构建
npm test                                 # vitest 单元测试

# 前后端联调
# 1) 启动后端：cd backend && uvicorn main:app --port 8080
# 2) 启动前端：cd frontend && npm run dev
# 3) 前端 dev server 已配 Vite 代理，/api 自动转发到 http://localhost:8080
#    浏览器访问 http://localhost:5175（前端调用 /api/...，无需处理 CORS）
```

> 说明：环境使用 `EStudy` conda 环境（Python 3.11），命令中用其 Python；依赖管理用 `requirements.txt`（运行时）+ pytest/ruff（开发）。不引入 uv/poetry/Redis/消息队列等额外组件。

## 10. 测试规范（详细设计 Pt.3 §20）

- **单元测试**优先覆盖确定性逻辑：`Parser / Chunker / RAG Retriever / Question Validator / Answer Checker / Permission Checker`。
- **Agent 测试**不比较完整字符串，只验证输出结构（如：是否产出 10 道题、题型是否正确、每题是否有答案）。
- **核心流程测试**至少三条：
  1. 资料导入：PDF → 解析 → 知识点 → 思维导图 → RAG
  2. AI 出题：资料 → RAG → Question Agent → Review Agent → 题库
  3. 刷题：题库 → 答题 → 判题 → 错题

```bash
# 后端测试
cd backend && python -m pytest

# 前端测试（Vitest）
cd frontend && npm test
```

## 11. 修改代码后的验证要求

每次修改完成后，**必须**按以下顺序验证：

1. **类型检查 / 静态检查**：确保无类型错误。
2. **单元 / Agent 测试**：运行对应测试，确认无回归。
3. **后端启动自检**：`/api/health` 返回正常，数据库可初始化。
4. **前端构建 / 启动自检**：能正常 `dev` 启动、无编译错误。
5. **LLM 相关改动**：额外确认输出经过三层校验、Review 重试上限生效、Token 未超限。
6. 验证通过后再汇报，不要在未验证的情况下声称“已完成”。

## 12. 编码规范要点

- **命名**：Python 遵循 PEP 8；前端遵循 Vue 3 组合式 API 约定。
- **确定性逻辑用普通函数/服务**，禁止为确定性任务引入 LLM 调用。
- **错误处理**：Agent 节点失败写入 `TaskState.errors`，经 `Result Handler` 汇总，不得静默吞错。
- **日志**：Agent 任务记录 `task_id / user_id / agent_name / node_name / start_time / end_time / status / error`（正式环境注意脱敏与 Token 成本）。
- **安全**：密码只存 Hash；上传文件校验扩展名/MIME/大小；JWT_SECRET、ENCRYPTION_KEY、API Key 一律走 `.env`，禁止硬编码或提交。

## 13. 项目进度与当前状态（P0 已完成，P1 冲刺进行中）

> 2026-08-14：项目正式更名 **EStudy**（原 StudyForge）；P0 缺口修补完成（上传自动索引/auth 同步/文档对齐）；四人五天 P1 分工见 `docs/开发任务分工.md`。

### 13.1 阶段完成情况

| 阶段 | 内容 | 状态 |
|---|---|---|
| P0-0 | 遗留代码审计 + 基线测试 + 数据质量检查 | ✅ |
| P0-1 | FastAPI 骨架 + 数据模型（SQLAlchemy + Alembic）| ✅ |
| P0-2 | 用户系统（JWT 认证 + refresh 轮换）| ✅ |
| P0-3 | 题库（CRUD + 软删除 + 权限隔离）| ✅ |
| P0-4 | 文档解析 + 知识提取 + 思维导图 | ✅ |
| P0-5 | RAG / Chroma（chunk + embedding + 检索）| ✅ |
| P0-6 | AI 出题 + 审题（LLMService + 三层校验）| ✅ |
| P0-7 | 刷题 + 错题（自动判题 + FSRS-6 + 记录）| ✅ |
| P0-8 | Navigator + Orchestrator（LangGraph）| ✅ |
| P0-9 | Vue 3 前端迁移 + 前后端联调 | ✅ |

### 13.2 测试结果（当前基线）

- **后端**：`164` 个测试全部通过（含核心闭环集成测试 `test_integration.py`、上传自动索引测试、FSRS 行为测试 `test_fsrs.py`），`ruff check` 全绿。
- **前端**：`10` 个单元测试通过，`vue-tsc` 类型检查与 `vite build` 均成功。
- **联调**：后端 `/api/health` 正常、前端页面 200、Vite 代理 `/api` → 后端 8080 转发成功。

### 13.3 已知遗留问题（P1 及以后评估）

> 完整进度与未完成清单见 `docs/项目进度.md`（滚动更新）。

1. ~~短答案（short_answer）未自动判题~~：✅ 已实现 LLM 判分（`grading.grade_short_answer`），LLM 未配置/异常时降级为用户自评。
2. **填空题精确匹配**：多答案/近义不判对，需 LLM 或答案拆分。
3. ~~154 道内置题数据质量/题型单一（#17）~~：✅ 内置题库已整体替换为《深入理解 AI Agent》第 1-2 章题库（22 题，覆盖单选/多选/判断/填空/简答，`seed/agent_bank.py` + 重写 `seed/seed.py`）。seed 同时创建开发者账号 `dev` / `dev123456`（仅本地测试）。
4. **PDF 解析未经真实 PDF 验证**；**图片解析未实现**（等视觉 Agent）。
5. ~~Knowledge/Document 语义化 Agent 未做~~：✅ 已迁移导入 Agent（`workflow/import_graph.py` + `structure_extract.py` + `knowledge_extract_service.py`），规则引擎 + 抽样交叉验证 + LLM 决策，配置 `DEEPSEEK_API_KEY` 后上传自动启用。
6. **刷题 session 恢复未做**（localStorage）；**无 Playwright E2E**（冒烟脚本代替）。
7. **无 LangGraph checkpoint 持久化**（内存态）；事务边界依赖 route commit。
8. **真实 DeepSeek 调用未在测试中触发**（用 Mock LLM）；`llm_model` 默认 `deepseek-chat` 需与实际账号确认。
9. ~~审计 P3 小项之 auth store `loggedIn` 不同步、seed 题型单一~~：✅ 已修复（`client.ts` 广播 auth-invalid 事件 + store 监听；内置题库已替换）。剩余小项：列表无分页、软删题的错题仍显示、错题筛选未下沉后端（详见 `docs/问题小结.md` #11~#14）。

> P1 规划功能（AI 错因分析/薄弱知识点强化/AI 导师/知识图谱/掌握度/热力图）均未开始，仅 `/api/stats` 有雏形。
