# StudyForge —— 智能题库与学习系统

面向大学生期末复习场景，通过 AI Agent 将课程资料（提纲、课件、教材等）自动转化为结构化学习资源：

> **上传学习资料 → 自动生成知识结构、思维导图、题库 → 刷题与错题记录形成学习闭环。**

统一入口为 **Navigator Agent**：理解用户意图并调度专业 Agent（Document / Knowledge / Question / Review）。

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3 + TypeScript + Vite + Tailwind 3 + Pinia + vue-router + markmap + KaTeX |
| 后端 | Python 3.11 + FastAPI + SQLAlchemy 2.0 + Alembic |
| Agent 编排 | LangGraph（聊天工作流 + 导入工作流） |
| 数据库 | SQLite（业务数据）+ Chroma（RAG 向量检索） |
| 模型 | DeepSeek（文本理解/出题/审核/判分）；千问视觉（图片解析，后置） |
| 认证 | JWT access（15min）+ refresh 轮换（30 天，哈希落库），bcrypt |

## 项目结构

```text
agent-quiz/
├── 启动.bat                    # 一键启动（后端 8000 + 前端 5173）
├── AGENTS.md                   # AI 编程工具开发规范
├── README.md
│
├── backend/                    # FastAPI 后端
│   ├── main.py                 # 应用入口（路由注册 + CORS + 全局异常处理）
│   ├── config.py               # pydantic-settings，统一从 .env 读取
│   ├── api/                    # 12 个 Router：auth/workbooks/questions/knowledge/
│   │                           #   documents/rag/review/agent/wrong_records/stats
│   ├── services/               # 业务层：access(权限)/grading(判题)/sm2/generation/
│   │                           #   rag/stats/structure_extract(规则引擎)/
│   │                           #   knowledge_extract(抽样交叉验证) 等
│   ├── repositories/           # 数据访问层（纯 CRUD）
│   ├── models/                 # 12 张表 ORM + enums（唯一真相源）
│   ├── schemas/                # Pydantic 请求/响应模型
│   ├── workflow/               # LangGraph：graph.py(聊天/出题) + import_graph.py(导入)
│   ├── rag/                    # chunker / embedding / chroma / retriever
│   ├── parsers/                # pdf / markdown / word / ppt 解析（image 后置）
│   ├── seed/                   # 种子：系统账号 + 内置 Agent 题库（agent_bank.py）
│   ├── alembic/                # 数据库迁移
│   ├── tests/                  # 168 个后端测试
│   └── data/                   # SQLite(quiz-app.db) + uploads/ + chroma/
│
├── frontend/                   # Vue 3 前端
│   └── src/
│       ├── api/                # fetch 封装（Bearer token + 401 自动刷新）
│       ├── stores/             # Pinia（auth）
│       ├── router/             # 路由 + 登录守卫
│       ├── views/              # 11 个页面：登录/注册/仪表盘/题库/刷题/错题本/
│       │                       #   思维导图/统计/上传/设置/添加题目
│       ├── components/         # MarkdownContent（消毒渲染）/ MindMap / RatingButtons
│       ├── lib/                # markdown(KaTeX+XSS 防护) / grading / darkMode
│       └── __tests__/          # vitest 单元测试
│
└── docs/                       # 项目文档
    ├── 项目需求说明书.md         # 需求 + P0/P1/P2 范围
    ├── 总体设计文档.md           # 六层架构 + Agent 架构
    ├── 详细设计Pt.1-3.md        # 数据/接口/Agent 详细设计
    ├── 新数据模型设计.md         # 12 表数据模型定稿
    ├── 问题小结.md              # 全项目代码审计报告（问题清单 #1~#17）
    ├── P0审计与整改计划.md / P0整改总计划.md
    ├── 后端反向解构报告.md
    └── 项目进度.md              # ★ 滚动进度快照与未完成清单
```

## 快速开始

前置：conda 环境 `EStudy`（Python 3.11）、Node.js。

```bash
# 方式一：双击 启动.bat（自动起后端 8000 + 前端 5173 并打开浏览器）

# 方式二：手动
cd backend && uvicorn main:app --reload        # 后端 http://localhost:8000
cd frontend && npm install && npm run dev      # 前端 http://localhost:5173
```

浏览器访问 <http://localhost:5173>（前端已配 Vite 代理，`/api` 自动转发到 8000）。

### 内置数据与测试账号

```bash
cd backend && python -m seed.seed
```

- **内置题库**（系统工作簿 id=0，全员可见只读）：《深入理解 AI Agent》第 1-2 章，
  22 题（单选/多选/判断/填空/简答）+ 15 个知识节点
- **开发者账号**：`dev` / `dev123456`（仅本地测试）

### 环境变量（backend/.env）

```text
DEEPSEEK_API_KEY=   # AI 出题/审题/简答判分/导入 Agent 所需（未配置时这些功能返回 503 或自动降级）
JWT_SECRET=         # 生产环境必须覆盖默认值
# 可选：QWEN_API_KEY / LLM_MODEL / EMBEDDING_MODEL / DATABASE_URL / MAX_FILE_SIZE ...
```

## 测试与检查

```bash
# 后端：168 测试 + 静态检查
cd backend && python -m pytest && python -m ruff check .

# 前端：单元测试 + 类型检查 + 构建
cd frontend && npm test && npm run build
```

## 核心功能

- **资料导入**：PDF / Word / PPT / Markdown / TXT / HTML（≤10MB）；图片解析后置
- **导入 Agent**：规则引擎 + LLM 抽样交叉验证提取知识点；无章节文档由 Document Agent 做 LLM 章节理解；三层校验 + 失败回环
- **AI 出题/审题**：按练习册/知识点/题型/数量生成，Review Agent 审核，FAIL 回环重试
- **刷题**：宽松/普通/严格三模式，选择/判断/填空自动判题，简答题 LLM 判分（未配 key 降级为自评），SM-2 间隔重复
- **错题本**：答错自动收集，错因编辑/筛选/收藏
- **统计**：掌握度分布、知识点热力图、错因分类、本周学习时长
- **思维导图**：知识树 markmap 可视化
- **Navigator Agent**：统一聊天入口（出题/生成导图/列文档/问答）

详细进度与未完成清单见 `docs/项目进度.md`；开发规范见 `AGENTS.md`。
