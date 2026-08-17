# EStudy 反向拆解教学笔记

> 本笔记基于 EStudy 当前代码、AGENTS.md、docs/ 设计文档、接口契约和进度记录整理。
> 用途：从“用 AI 完成开发”提升到“真正理解项目设计和技术路线”，用于简历与面试准备。
> 注意：文中会区分“已实现”和“设计规划”，避免把计划说成已实现。

---

## 第一部分：项目整体认知

### 1. EStudy 解决什么问题？

一句话：

> **大学生期末复习时，手里有老师的 PDF/PPT/Word 资料，但没有知识结构、没有思维导图、没有针对自己资料的题库、错题也不会自动归纳。EStudy 把“资料”变成“一套可刷题、可追踪掌握度的学习系统”。**

核心链路（AGENTS.md 和总体设计文档里都明确写了）：

```text
上传学习资料
  → 文档解析
  → 知识提取
  → 思维导图
  → RAG 语义检索
  → AI 出题 + AI 审题
  → 题库
  → 刷题
  → 错题记录
  → FSRS 复习调度
  → 统计/诊断/推荐
```

### 2. 核心用户场景

- 学生上传课程 PDF / Word / PPT / Markdown。
- 系统自动抽出章节和知识点，生成知识树 + 思维导图。
- 学生说“帮我出 10 道反向传播选择题”，主 Agent 检索资料、调用出题专家、生成并审题，先给提案，用户确认后入库。
- 学生刷题，系统自动判题；答错自动进错题本；FSRS-6 安排复习时间。
- 学生问“我哪里薄弱”，系统聚合答题记录 + 错题，做诊断和推荐。

### 3. 整体技术路线

| 层 | 技术 |
|---|---|
| 前端 | Vue 3 + Vite + TypeScript + Pinia + Tailwind CSS |
| 后端 | FastAPI + SQLAlchemy 2.0 + Alembic |
| Agent 编排 | LangGraph（`create_react_agent` + 专家子图/Pipeline） |
| 业务数据库 | SQLite |
| 向量数据库 | Chroma + 本地 ONNX MiniLM embedding |
| LLM | DeepSeek（文本/function calling） |
| 视觉模型 | 千问视觉（图片解析，当前部分预留） |
| 复习算法 | FSRS-6（py-fsrs） |

### 4. 为什么选择当前技术栈？

- **FastAPI 而不是 Express/Spring**：项目是 Python 技术栈，LLM 生态（LangChain/LangGraph）在 Python 最成熟；FastAPI 自带 Pydantic 校验、OpenAPI 文档、依赖注入，非常适合“API 层薄、业务层清晰”的分层单体。
- **Vue 3 + Vite 而不是 React**：项目早期有 React/Express 版本，后来 2026-08-14 明确删除旧前端，迁移到 Vue 3。对个人项目来说 Vue 上手快、模板直观、和 Vite 组合开发体验好；团队里也统一到 Vue。
- **SQLite + Chroma 双库分离**：SQLite 存“结构化业务事实”，Chroma 存“向量语义”。个人项目/教学项目不需要上 PostgreSQL + Milvus，本地可跑、可测试、可部署。
- **LangGraph 而不是裸 LangChain chain**：因为系统需要一个“主 Agent 决策 + 专家固定 Pipeline”的混合架构，LangGraph 适合表达状态图、条件路由、重试回环。
- **FSRS-6 而不是简单 SM-2**：SM-2 是经典间隔重复，但 FSRS 是数据驱动的现代调度算法，能根据用户历史优化记忆参数，作为简历亮点更硬。

### 5. 与普通错题本相比，AI 能力体现在哪里？

普通错题本：手动录入题目、手动打标签、手动看错题列表。

EStudy：

1. **资料自动转知识结构**：AI/规则从 PDF 里抽章节、知识点，生成导图。
2. **RAG 让 AI 基于你的资料回答**：不是通用大模型瞎编，而是先检索你自己的教材。
3. **AI 出题 + AI 审题**：根据知识点生成题目，再用另一个 LLM 审核，形成“提议者-审核者”闭环。
4. **自然语言操作**：用户不用点 7 次按钮，说一句“针对第三章错题出 5 道题”即可。
5. **学习闭环**：错题 → 错因分析 → 薄弱点诊断 → 补救题，这是普通错题本做不到的。

### 整体架构图（文字版）

```text
┌────────────────────────────────────────────────────────────┐
│ 表现层 Vue 3                                                │
│ Dashboard / 题库 / 刷题 / 错题本 / 思维导图 / 统计 / AI 助手    │
└──────────────────────────┬─────────────────────────────────┘
                           │ /api (fetch + JWT + 401 refresh)
┌──────────────────────────▼─────────────────────────────────┐
│ API 层 FastAPI                                              │
│ auth / workbooks / questions / knowledge / documents / rag  │
│ review / wrong_records / stats / agent / conversations      │
└──────────────────────────┬─────────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────┐
│ Agent 层                                                    │
│ 主 Agent（助手·导师，ReAct，唯一开放式决策）                    │
│   └── Tool Layer（读工具 / 写工具两阶段确认）                  │
│        ├── 知识专家：规则 + LLM 交叉验证 + 校验回环              │
│        ├── 出题专家：RAG → 生成 → 三层校验 → 审题 → 回环 ≤2    │
│        └── 教练专家：统计聚合 → LLM 归因 → 补救题（规划中）      │
└──────────────────────────┬─────────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────┐
│ Service 层（确定性业务）                                      │
│ document / knowledge / question / generation / review       │
│ grading / fsrs_scheduler / stats / rag / conversation       │
└──────────────────────────┬─────────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────┐
│ Repository 层（数据访问）                                     │
└──────────────────────────┬─────────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────┐
│ 数据层                                                      │
│ SQLite：users/workbooks/knowledge/questions/options          │
│         answer_records/wrong_records/review_cards/...       │
│ Chroma：向量片段（metadata 带 workbook_id/document_id）       │
└────────────────────────────────────────────────────────────┘
```

---

## 第二部分：完整数据流分析

### 数据流 A：用户上传学习资料

这是整个项目最核心的一条链路，代码位置很清晰。

#### 完整流程

```text
前端选择文件
  → POST /api/documents/upload (multipart)
  → document_service.upload_document
  → parsers.factory.detect_type + parse_file
  → 得到 ParsedDocument（title + sections[]）
  → 可选：workflow/import_graph（LLM 增强章节理解 + 知识提取）
  → _save_parsed：解析结果 JSON 落盘
  → knowledge_service.import_sections：写 Knowledge 树
  → rag_service.index_document：切块 → embedding → 写 Chroma
  → 返回 DocumentDetailOut
```

#### 每一步在哪里实现、用什么技术、为什么

| 步骤 | 代码位置 | 技术 | 为什么这样设计 |
|---|---|---|---|
| 1. 上传 | `frontend/src/api/index.ts` 的 `documentApi.upload` | XHR + FormData + 进度回调 | 大文件上传需要进度反馈；`client.ts` 统一带 JWT |
| 2. 接收 | `backend/api/documents.py` `upload_document` | FastAPI `UploadFile` | API 层只做参数解析和 `db.commit()` |
| 3. 文件类型识别 | `backend/parsers/factory.py` | 扩展名映射 `EXT_MAP` | 用一个工厂集中管理“什么后缀用什么 Parser” |
| 4. 文档解析 | `backend/parsers/pdf.py` / `markdown.py` / `word.py` / `ppt.py` | pypdf / markdown-it / python-docx / python-pptx | 解析是确定性能力，应该和 LLM 解耦，单独可测试 |
| 5. 统一中间表示 | `backend/parsers/base.py` | `ParsedDocument` + `Section` dataclass | 所有解析器输出同一结构，后续 RAG/知识树不关心来源格式 |
| 6. 知识增强 | `document_service._run_import_agents` → `workflow/import_graph.py` | LangGraph + LLM | 有 API Key 才启用；失败不阻断上传，保证核心链路可用 |
| 7. 解析结果落盘 | `_save_parsed` → `data/uploads/parsed/{doc_id}.json` | JSON 文件 | 避免每次重新解析；RAG 重建索引时直接读 |
| 8. 写知识树 | `knowledge_service.import_sections` | SQLAlchemy | 把章节/知识点变成 `knowledge` 表里的树节点 |
| 9. 自动索引 | `rag_service.index_document` | `chunk_document` → `embedding` → `VectorStore.upsert` | 2026-08-14 修复：以前上传后要手动点“重建索引”，现在自动做 |
| 10. 返回 | `DocumentDetailOut` | Pydantic | 前端拿到 sections 后可展示解析结果 |

#### 架构师视角：为什么这样设计？

- **解析和 AI 理解分开**：PDF 提取文字是确定性程序，不该浪费 LLM；LLM 只做“章节理解/知识点提取”这种语义任务。
- **知识树和向量库分开**：知识树是给人看的、可编辑的结构化资产；Chroma 是给机器检索的语义索引。两者通过 `document_id`/`knowledge_id` 关联。
- **上传主链路不被 AI 阻塞**：`_run_import_agents` 放在 try/except 里，AI 挂了至少还有规则引擎的结果。

---

### 数据流 B：用户刷题 → 错题 → 知识分析 → AI 推荐

#### 完整闭环

```text
前端 ReviewView 进入刷题
  → GET /api/review/due
  → review_service.get_due
  → 返回到期题目 + FSRS 卡片

用户提交答案
  → POST /api/questions/{id}/answer
  → review_service.answer_question
  → grading.grade_question（确定性判题）
  → answer_record_repository.create（每次作答都记）
  → 答错 → wrong_record_repository.record（错题本）
  → review_card_repository.get_or_create + fsrs_scheduler.apply_review

之后：
  → GET /api/stats：聚合正确率、掌握度热力图、错因分布
  → GET /api/wrong-records：错题本
  → 教练专家（规划中）：读错题 + 答题记录 → LLM 归因 → 补救题
```

#### 对应代码

| 环节 | 代码 |
|---|---|
| 到期题目 | `backend/services/review_service.py` `get_due` |
| 判题 | `backend/services/grading.py` |
| 答题记录 | `backend/models/answer_record.py` + `repositories/answer_record_repository.py` |
| 错题 | `backend/models/wrong_record.py` + `repositories/wrong_record_repository.py` |
| FSRS | `backend/services/fsrs_scheduler.py` + `models/review_card.py` |
| 统计 | `backend/services/stats_service.py` |
| 错因/推荐 | 目前 `stats_service` 里有正则关键词分类；`coach_service` 是设计文档里的 P1 规划，当前代码还没创建 |

#### 架构师视角：这个闭环为什么好？

- **题目和用户学习记录彻底分离**：`questions` 表没有 `user_id`、没有 `wrong_answer`。题是客观资产，错题是用户主观反思。这是从旧“错题本焊死题目”模型重构来的核心决策。
- **AnswerRecord 只增不改**：它是审计日志，统计/热力图都基于它。
- **WrongRecord 可编辑**：用户能改错因，未来 AI 分析基于这里。
- **FSRS 状态独立在 ReviewCard**：一人一题一卡，复合主键 `(question_id, user_id)`，调度算法和业务统计分开。

---

## 第三部分：Agent 架构学习

### 1. Agent 和普通后端接口有什么区别？

普通后端接口：**输入固定，流程固定**。比如 `POST /api/questions/{id}/answer`，你传答案，后端判题、写库、返回结果。每一步都是写死的。

Agent 接口：**输入是自然语言，执行路径由 LLM 决定**。比如 `POST /api/agent/chat` 传“帮我整理资料再出 5 道题”，后端不知道你要先检索、再调用知识专家、再调用出题专家；这些步骤是模型根据工具描述现场决定的。

EStudy 的关键设计原则（AGENTS.md §4）：

> 不是所有功能都 Agent 化。确定性逻辑（判题、FSRS、文件解析、权限）用普通 Service；只有“开放式交互/规划”才用 Agent。

### 2. ReAct 模式是什么？

ReAct = **Reasoning + Acting**，让 LLM 交替进行：

```text
Thought: 用户想做什么？我需要查什么资料？
Action: 调用 search_documents(query="反向传播")
Observation: 返回了 3 段资料
Thought: 现在有依据了，可以调用出题专家
Action: 调用 generate_questions(topic="反向传播")
Observation: 返回 proposal，等用户确认
...
Final Answer: 已生成 5 道题提案，请确认。
```

在 EStudy 中，`backend/workflow/graph.py` 直接用了 LangGraph 的 `create_react_agent`：

```python
def build_graph(db, user, llm=None, tools=None, agent_factory=None):
    llm_service = llm or get_llm()
    tool_list = tools if tools is not None else build_tools(db, user, llm_service)
    factory = agent_factory or create_react_agent
    return factory(
        model=llm_service.chat_model(),
        tools=tool_list,
        prompt=SUPERVISOR_PROMPT,
    )
```

`MAX_ITERATIONS = 8` 是熔断，防止模型死循环调用工具。

### 3. Tool 调用流程是什么？

代码链路：

```text
用户消息
  → POST /api/agent/chat
  → api/agent.py chat()
  → agent_service.run_task()
  → build_graph(db, user) 创建 ReAct Agent
  → runner.invoke({"messages": [HumanMessage(prompt)]})
  → LLM 决定调用哪个工具
  → LangGraph 执行 workflow/tools.py 里注册的 StructuredTool
  → 工具内部调用 Service → Repository → DB / Chroma
  → 工具返回 JSON 字符串
  → _collect_output() 从 messages 里提取 steps / proposals / reply
  → 返回给前端
```

`workflow/tools.py` 里目前真实实现的工具：

| 工具 | 类型 | 说明 |
|---|---|---|
| `search_documents` | 读 | RAG 检索 |
| `get_knowledge_tree` | 读 | 读知识树 |
| `get_knowledge_detail` | 读 | 读单个知识点 |
| `list_documents` | 读 | 列文档 |
| `get_questions` | 读 | 列题目 |
| `generate_questions` | 写 | 生成题目提案 |
| `add_knowledge_node` | 写 | 新增知识点提案 |
| `update_knowledge_node` | 写 | 修改知识点提案 |
| `delete_knowledge_node` | 写 | 删除知识点提案 |

设计文档里还规划了 `navigate`、`get_stats`、`get_due`、`analyze_wrong_reason`、`create_plan` 等，但当前 `tools.py` 还没全部实现。面试时要注意区分。

### 4. 两阶段确认为什么设计？

写操作有风险：AI 可能理解错，比如用户说“把这里改简单点”，AI 可能改错节点。如果 AI 一句话直接改库，错误不可挽回。

EStudy 的方案是 **propose → confirm**：

```text
用户说“删掉知识点 16”
  → 主 Agent 调用 delete_knowledge_node
  → 工具不删库，而是 proposal_service.create() 生成 proposal
  → 返回 { proposal_id, action, target, changes, impact, expires_in_sec }
  → 前端渲染确认卡片
  → 用户点“确认执行”
  → POST /api/agent/confirm { proposal_id, approved: true }
  → proposal_service.confirm() 才真正执行删除
```

代码在 `backend/services/proposal_service.py`：

- proposal 存在**内存 dict** 里，不是数据库；
- 有效期 600 秒；
- 绑定 user_id，跨用户确认返回 404；
- 只能消费一次；
- 确认时再次走 `access.get_owned_*` 权限校验。

为什么不用 LangGraph interrupt？文档里写得很清楚：interrupt 复杂、难测试；两阶段 API 简单、可单测、前端只需要一个通用确认卡片。

### 5. conversation 如何保存？

当前代码已经有 `conversations` 和 `conversation_messages` 两张表：

- `backend/models/conversation.py`
- `backend/repositories/conversation_repository.py`
- `backend/services/conversation_service.py`
- `backend/api/conversations.py`

流程：

```text
第一次聊天
  → /api/agent/chat 不传 conversation_id
  → agent_service 自动 create 一个 conversation
  → 用户消息和助手消息都 add_message
  → 返回 conversation_id

继续聊天
  → 前端传 conversation_id
  → agent_service 校验归属
  → 再次持久化新消息
```

**注意当前代码的一个真实缺口**：`agent_service.run_task` 虽然保存了历史消息，但**还没有把历史消息加载回 prompt**。也就是说，目前多轮“上下文延续”在代码里还没真正闭环。设计文档里规划“传 conversation_id 时自动加载”，但实际代码只做了归属校验和落库。这是面试时你能展示“我清楚现状和设计的差距”的好例子。

### 6. 后续专家 Agent 为什么这样设计？

EStudy 不是“6 个 Agent 各自乱转”，而是：

```text
1 个主 Agent（唯一 ReAct，负责开放决策）
+ 3 个专家（内部固定 Pipeline，不决策）
```

- **知识专家**：`workflow/import_graph.py`，规则引擎预提取 → 抽样 → LLM 交叉验证 → 校验回环 ≤2。
- **出题专家**：`generation_service.py`，RAG → 生成 → 三层校验 → LLM 审题 → 回环 ≤2 → 入库。
- **教练专家**：设计为统计聚合（确定性）→ LLM 归因 → 条件分支 → 调出题专家；当前 `coach_service.py` 还没创建。

为什么这样设计？

1. **省 Token**：固定流程不需要每一步都问 LLM“下一步干嘛”。
2. **可测试**：出题/审题/FSRS 是确定性 Pipeline，可以写断言。
3. **可解释**：专家内部回环上限是规则，不是模型自由发挥。
4. **对外叙事仍是多 Agent**：主 Agent 调度专家，教练又能调出题专家，形成协作。

---

## 第四部分：RAG 技术路线学习

### 1. 数据如何进入知识库？

上传文档后自动触发：

```text
document_service.upload_document
  → rag_service.index_document
  → 读解析后的 sections
  → chunker.chunk_document()
  → embedding.get_embedder().embed_documents()
  → VectorStore.upsert() 写入 Chroma
```

代码在 `backend/services/rag_service.py`、`backend/rag/`。

### 2. 文档如何切片？

`backend/rag/chunker.py`：

- 按“章节 → 段落 → 固定长度”的层次切；
- `chunk_size = 500`（settings 可配）；
- 每个 chunk 带 `section` 和 `knowledge_id`；
- chunk_id 形如 `d{document_id}-s{section_index}-c{chunk_index}`，保证可追踪。

为什么按章节切？因为教材的知识边界通常在章节内；再按 500 字固定长度切是为了控制 embedding/LLM 的输入长度。

### 3. embedding 如何生成？

`backend/rag/embedding.py`：

- 默认 `ChromaEmbedder`，使用 Chroma 自带的本地 ONNX `all-MiniLM-L6-v2`；
- 不需要 API Key，离线可用，成本为零；
- 通过 `settings.embedding_model` 注入，未来可换 sentence-transformers 或云端 embedding。

### 4. 向量如何存储？

`backend/rag/chroma.py`：

- `chromadb.PersistentClient(path=settings.chroma_path)`
- collection 名为 `studyforge`
- 使用 cosine 距离
- metadata 里带：

```python
{
  "workbook_id": ...,
  "document_id": ...,
  "section": ...,
  "knowledge_id": ...   # 可选
}
```

这个 metadata 是隔离的关键：不同用户/不同练习册的向量不会互相污染。

### 5. 查询如何检索？

`backend/rag/retriever.py`：

```text
query
  → embed_query(query)
  → VectorStore.query(where={"workbook_id": ...})
  → 可选再加 knowledge_id 过滤
  → 返回 top_k 个 chunk
```

`rag_service.retrieve()` 会先做权限校验 `access.get_visible_workbook()`，防止用户检索到别人的资料。

### 6. LLM 如何结合上下文回答？

有两种用法：

1. **出题**：`rag_service.build_context()` 把 RAG 片段拼成 prompt 上下文，再交给 `generation_service` 生成题目。
2. **答疑/主 Agent**：主 Agent 的 `search_documents` 工具返回 RAG 片段，LLM 基于片段回答。

关键点：**长文档不直接塞给 LLM，只把检索到的 top-k 片段给 LLM**。

### 7. 为什么 RAG 适合这个项目？

- LLM 没读过用户教材，RAG 让回答/出题基于用户自己的资料。
- 整本教材塞不进 prompt，RAG 只取最相关的 3-5 段。
- 用户资料是私有的、持续增加的，RAG 比微调更灵活。
- 本地 embedding 成本低，个人项目可跑。

### 8. 有哪些替代方案？

| 方案 | 优点 | 缺点 | 为什么不选 |
|---|---|---|---|
| 直接全量塞 prompt | 简单 | token 爆炸、贵、超限 | 教材太长 |
| 微调模型 | 能让模型“记住”资料 | 成本高、资料频繁变、需要训练数据 | 个人项目不划算 |
| 长上下文模型 | 不用切片 | 仍贵、检索精度不如 RAG、上下文窗口有限 | 当前模型/成本不合适 |
| GraphRAG/知识图谱增强 | 能利用关系 | 工程复杂度高 | 当前知识树已够用，知识图谱是 P3 远期 |
| 混合检索（BM25 + 向量） | 提高关键词精确匹配 | 需要多维护一个索引 | 当前阶段向量够用，未来可加 |

---

## 第五部分：后端工程学习

### 1. 分层职责

EStudy 后端是严格的 FastAPI 分层单体：

```text
API（Router）→ Service → Repository → Model → SQLite
                    ↘ RAG / Parser / Workflow（横向能力）
```

| 层 | 职责 | EStudy 位置 |
|---|---|---|
| Router | 参数校验、调 Service、`db.commit()`、返回响应 | `backend/api/*.py` |
| Service | 业务逻辑、权限、编排、确定性算法 | `backend/services/*.py` |
| Repository | 单表/单查询的 ORM 操作，不写业务 | `backend/repositories/*.py` |
| Model | SQLAlchemy 表结构，唯一 schema 真相源 | `backend/models/*.py` |
| Schema | Pydantic 请求/响应模型 | `backend/schemas/*.py` |

### 2. 结合真实模块讲解

#### 2.1 question 模块

一次“更新题目”请求：

```text
PUT /api/questions/{id}
  → api/questions.py update_question()
  → question_service.update_question()
  → access.get_owned_question() 权限校验
  → question_repository.get_by_id()
  → question_option_repository.replace()
  → db.commit()
```

#### 2.2 wrong_record 模块

```text
GET /api/wrong-records
  → api/wrong_records.py
  → wrong_record_service
  → wrong_record_repository + question_repository
  → 联查题干/答案/知识点
```

#### 2.3 conversation 模块

```text
GET /api/conversations
  → api/conversations.py
  → conversation_service.list_conversations()
  → conversation_repository.list_by_user()
  → 每条会话取 last_message
```

#### 2.4 knowledge_graph / knowledge 模块

- 当前主体是 **知识树**：`knowledge` 表自引用 `parent_id`。
- 新增了 `knowledge_relations` 表（`backend/models/knowledge_relation.py`），记录知识点之间的语义关系，对应 Issue #58 知识图谱。
- 路由：`GET /api/knowledge`、`GET /api/knowledge/{id}`、`GET /api/workbooks/{id}/mindmap`。

一次“读思维导图”请求：

```text
GET /api/workbooks/{id}/mindmap
  → mindmap_service
  → knowledge_repository 读树
  → 组装 MindMapNode
```

### 3. 事务边界

当前约定：**Service 只 flush，Router 层 commit**。例如：

```python
@router.post("/questions", status_code=201, response_model=QuestionOut)
def create_question(...):
    out = question_service.create_question(db, user, body)
    db.commit()
    return out
```

这是 P3 质量债之一：设计上未来要显式引入 Unit of Work，但当前用“Router 统一 commit”已经能保证单请求内的事务完整性。

---

## 第六部分：前端工程学习

### 1. 页面如何组织

`frontend/src/views/` 下按业务页面组织：

```text
LoginView / RegisterView
DashboardView          # 仪表盘
QuestionBankView       # 题库
AddQuestionView        # 手动加题
ReviewView             # 刷题
WrongBookView          # 错题本
MindMapView            # 思维导图
StatsView              # 统计/热力图
HistoryView            # 学习活动时间线
AgentChatView          # AI 助手
SettingsView           # AI 设置
```

路由在 `frontend/src/router/index.ts`，带登录守卫：

```ts
router.beforeEach((to) => {
  if (!isAuthenticated() && to.path !== '/login' && to.path !== '/register') {
    return '/login'
  }
  return true
})
```

### 2. 状态如何管理

- 使用 **Pinia**，目前主要是 `stores/auth.ts`。
- 登录状态由 `auth` store 管理。
- 其他页面多数是组件内本地状态 + API 直接返回。

### 3. API 如何调用

- `frontend/src/api/client.ts`：封装 fetch，自动带 JWT，401 时自动用 refresh token 刷新，刷新失败广播 `estudy:auth-invalid`。
- `frontend/src/api/index.ts`：按业务域封装 `authApi` / `questionApi` / `agentApi` / `conversationApi` 等。

```ts
export const agentApi = {
  chat: (message, options) => api.post('/agent/chat', body),
  confirm: (proposalId, approved) => api.post('/agent/confirm', {...}),
}
```

### 4. Agent 聊天页面如何实现

`frontend/src/views/AgentChatView.vue`：

- 左侧会话列表；
- 中间消息流；
- 助手消息支持 Markdown 渲染（`MarkdownContent.vue`）；
- 每条助手消息可展开“执行步骤 steps”；
- 写操作渲染通用确认卡片；
- 收到 `navigate` 时 `router.push()`。

核心交互：

```text
send()
  → agentApi.chat(msg, { workbookId, conversationId, context })
  → 把 resp.reply 推入 messages
  → 把 resp.steps 展示为执行步骤
  → 把 resp.proposals 渲染为确认卡片
  → 用户点击确认 → agentApi.confirm(proposalId, true)
```

### 5. 数据可视化如何实现

- **思维导图**：`components/MindMap.vue` 使用 markmap 渲染知识树。
- **学习热力图**：`components/HeatmapCalendar.vue` + `StatsView.vue`，数据来自 `GET /api/stats`。
- **统计页**：正确率分布、知识点掌握度热力图、错因分布、最近记录。

---

## 第七部分：面试准备

### 简历版本（3-5 条）

1. **EStudy 智能题库与学习系统**：独立设计并实现面向大学生期末复习的 AI 学习平台，核心链路为“上传资料 → 知识提取 → 思维导图 → RAG 检索 → AI 出题/审题 → 刷题 → FSRS 复习调度 → 错题诊断”。

2. **后端分层架构**：基于 FastAPI + SQLAlchemy + Alembic 实现严格分层后端（API → Service → Repository → Model），完成 JWT 双令牌认证、权限隔离、文档解析、RAG、题库、刷题、统计等 20+ 接口；171 个后端测试全绿。

3. **LangGraph Agent 架构**：采用“1 个 ReAct 主 Agent + 3 个领域专家 Pipeline”的混合架构；主 Agent 通过工具层调用 Service，写操作使用 propose→confirm 两阶段确认保证数据安全；实现对话历史持久化与会话管理。

4. **RAG 知识检索**：使用 Chroma + 本地 ONNX embedding 实现基于用户私有资料的语义检索，支持 workbook/knowledge 级隔离，为 AI 出题和答疑提供上下文，避免 LLM 凭空生成。

5. **Vue 3 前端**：使用 Vue 3 + TypeScript + Pinia + Tailwind 开发 11 个页面，包括 AI 聊天页、思维导图、刷题、错题本、学习热力图；封装带 JWT 自动刷新的 API client。

### 面试高频问题（20+）

下面每个问题都给出“普通回答”和“深入回答”。

#### 1. 为什么采用 Agent 而不是普通接口？

- 普通回答：因为用户输入是自然语言，路径不固定，需要 AI 自主规划。
- 深入回答：EStudy 里只有“开放式交互”用 Agent，其他确定性功能都是普通 Service。主 Agent 用 ReAct 决定“先检索还是先出题”；而判题、FSRS、文件解析仍然是普通函数。这样既保留灵活性，又让核心算法可测试、可复现。

#### 2. RAG 解决什么问题？

- 普通回答：让 LLM 基于用户自己的资料回答，而不是瞎编。
- 深入回答：LLM 没有读过用户教材，且整本教材塞不进 prompt。EStudy 上传时把文档切块、embedding、存 Chroma；使用时检索 top-k 片段再交给 LLM。metadata 里带 `workbook_id`，实现用户数据隔离。

#### 3. 如何保证 Agent 输出可靠？

- 普通回答：做校验和审核。
- 深入回答：三层校验（格式 → 结构 → 业务）+ 出题专家内部 LLM 审题 + 回环上限 ≤2 + 写操作两阶段确认。例如 `question_validator.py` 会检查选择题选项数、答案是否在选项中、非选择题不能带选项。

#### 4. 如何设计上下文管理？

- 普通回答：把用户消息、workbook、页面上下文传给 Agent。
- 深入回答：请求带 `{ message, workbook_id, context: { route, entity } }`，system prompt 明确“这里/这个”优先读 context。对话历史设计为 `conversations` + `messages` 两表，消息 metadata 存 steps/proposals。当前代码已持久化历史，但历史加载回 prompt 还在完善中。

#### 5. 如何处理多轮对话？

- 普通回答：保存历史消息，下次带上。
- 深入回答：`conversation_id` 由后端创建并返回；每次 chat 落库 user/assistant 两条消息；未来把历史 messages 加载进 LangGraph 的 messages state。当前实现已能“新建/切换/删除会话”，但多轮历史真正注入模型还需要补齐。

#### 6. 数据库如何设计？

- 普通回答：有用户、题库、错题、复习卡等表。
- 深入回答：核心是“题目本身”和“用户学习记录”分离。`Question` 不含 `user_id`、`wrong_answer`；`AnswerRecord` 只增不改；`WrongRecord` 可编辑；`ReviewCard` 复合主键 `(question_id, user_id)`。外键删除策略：组合关系 CASCADE，历史记录 RESTRICT，知识父节点 SET NULL。

#### 7. 如何保证系统扩展性？

- 普通回答：分层、模块化。
- 深入回答：API → Service → Repository 单向依赖，Agent 不直接 SQL；RAG、Parser、Workflow 是横向能力；专家内部 Pipeline 可独立替换；未来可把 SQLite 换 PostgreSQL、Chroma 换 Milvus、本地 embedding 换云端，而不需要改业务层。

#### 8. 为什么用 SQLite + Chroma 而不是 MySQL + Elasticsearch？

- 普通回答：项目简单、本地可跑。
- 深入回答：SQLite 存结构化业务数据足够；Chroma 存向量，支持 cosine 和 metadata filter。个人项目不需要中间件，部署成本低；但通过 Repository 层隔离，未来可平滑迁移。

#### 9. 为什么用 LangGraph 而不是 LangChain Chain？

- 普通回答：LangGraph 适合有状态、有条件分支的流程。
- 深入回答：EStudy 需要 ReAct 主循环 + 专家重试回环 + 条件路由。LangGraph 的 `StateGraph` 能表达 `START → navigator → conditional_edges → agent → retry/END`，并且状态通过 TypedDict 传递，比 Chain 更可控。

#### 10. 什么是 ReAct？

- 普通回答：Reasoning + Acting，让模型思考后调用工具。
- 深入回答：EStudy 的 `create_react_agent` 让 LLM 交替输出 thought/action/observation，工具结果作为 observation 回到模型。`MAX_ITERATIONS=8` 防止死循环。

#### 11. 工具层怎么设计？

- 普通回答：封装成函数给 Agent 调用。
- 深入回答：`workflow/tools.py` 用 `StructuredTool` + Pydantic args_schema，工具是 Service 的薄封装（≤30 行），参数带语义引导（如 `topic`）。读写分级：读工具直接执行，写工具返回 proposal。

#### 12. 两阶段确认怎么实现？

- 普通回答：先给预览，用户确认再执行。
- 深入回答：`proposal_service` 用内存 dict 存 proposal，绑定 user_id，TTL 600 秒，一次性消费；`confirm` 时再次权限校验。测试覆盖“propose 不落库、confirm 才落库”。

#### 13. 如何防止用户 A 看到用户 B 的数据？

- 普通回答：查询时过滤 user_id。
- 深入回答：`access.py` 提供 `get_owned_*` / `get_visible_*`；系统工作簿 id=0 所有用户只读，其余仅属主可读写；RAG 检索时也先校验 workbook 可见性。stats 查询会 join 可见题库再按 user_id 过滤。

#### 14. 出题质量怎么保证？

- 普通回答：让另一个 LLM 审核。
- 深入回答：出题专家 Pipeline 是“RAG 检索 → LLM 生成 → 结构/业务校验 → LLM 审题 → 重试 ≤2 → 入库”。`generation_service.MAX_ATTEMPTS=3` 控制最多尝试次数；`question_validator.py` 做确定性校验。

#### 15. 简答题怎么判分？

- 普通回答：用 LLM 判。
- 深入回答：`grading.grade_short_answer` 调用 LLM 输出 `{correct: bool}`；空白直接判错；LLM 未配置/异常时返回 None，前端降级为用户自评。这是“AI 能力 + 确定性降级”的典型设计。

#### 16. FSRS 是什么？为什么用它？

- 普通回答：间隔重复算法，安排复习时间。
- 深入回答：FSRS-6 是数据驱动的记忆调度算法，比 SM-2 更精准。`fsrs_scheduler.py` 封装 py-fsrs，评分四档 again/hard/good/easy，数据库存 state/step/stability/difficulty/due。EStudy 从 SM-2 迁移到 FSRS-6 是一个真实的技术演进点。

#### 17. 文档解析怎么设计？

- 普通回答：按扩展名选解析器。
- 深入回答：`parsers/factory.py` 是工厂模式，所有 Parser 输出统一 `ParsedDocument`；PDF 用 pypdf 提取文本 + 启发式章节切分；解析是确定性 Service，AI 只做增强提取，失败不阻断上传。

#### 18. 知识提取怎么做？

- 普通回答：让 LLM 提取知识点。
- 深入回答：`structure_extract.py` 是 0 LLM 的规则引擎（标题/定义/对比/列表正则）；`knowledge_extract_service.py` 做规则预提取 → 均匀抽样 → LLM 交叉验证 → 决策是否全量提取；`import_graph.py` 是 LangGraph Pipeline，校验失败回环 ≤2，全量提取上限 30 块。

#### 19. 对话历史表结构为什么这样设计？

- 普通回答：会话和消息分两张表。
- 深入回答：`conversations` 存会话元数据（user_id, title），`conversation_messages` 存消息正文和 `metadata` JSON（steps/proposals/navigate）。这样历史消息可以恢复完整聊天 UI，而不只是文本。

#### 20. 如何做前端权限控制？

- 普通回答：路由守卫。
- 深入回答：`router.beforeEach` 检查 `isAuthenticated()`；API client 每次请求带 JWT，401 时自动 refresh；refresh 失败广播 `estudy:auth-invalid`，Pinia store 同步登出。真正数据权限还是后端 `access.py` 保证，前端只是体验层。

#### 21. 如果让你重构，你会改哪里？

- 普通回答：优化代码结构。
- 深入回答：我会优先补：① 对话历史真正注入多轮 prompt；② 显式 Unit of Work 替代 Router 层 commit；③ 工具层补齐文档里规划的 `navigate/get_stats/get_due/analyze_wrong_reason`；④ proposal 从内存搬到 Redis/DB，支持多实例；⑤ 删除文档时同步清理 Chroma 向量的一致性测试。

#### 22. 这个项目最大的技术难点是什么？

- 普通回答：AI 相关。
- 深入回答：不是“调 API”，而是**如何把不确定的 LLM 放进一个确定性的工程系统**。EStudy 的解法是：只有主 Agent 开放决策；专家内部固定 Pipeline；LLM 输出三层校验；写操作两阶段确认；确定性算法（判题/FSRS/解析）绝不 Agent 化。这套“AI 与工程结合”的边界设计才是项目核心难点。

---

## 第八部分：个人学习路线

按优先级排序。目标不是“会跑项目”，而是“能独立从零设计”。

### 第一优先级：后端基础 + 项目主干

1. **Python + FastAPI**
   - 学：路由、依赖注入、Pydantic、异常处理。
   - 在项目里读：`backend/main.py`、`backend/api/*.py`、`backend/schemas/*.py`。

2. **SQLAlchemy + 数据建模**
   - 学：ORM、关系、外键删除策略、事务。
   - 在项目里读：`backend/models/*.py`、`docs/新数据模型设计.md`。
   - 重点理解“题目 vs 学习记录分离”和“单一事实源”。

3. **分层架构**
   - 学：API → Service → Repository → Model 的职责边界。
   - 在项目里读：`backend/services/question_service.py` + `backend/api/questions.py`。
   - 自问：如果新增一个“导出题库为 JSON”功能，代码应该放哪一层？

### 第二优先级：RAG 与 LLM 工程

4. **RAG 原理 + 向量数据库**
   - 学：切块、embedding、相似度检索、metadata filter。
   - 在项目里读：`backend/rag/` 四个文件 + `backend/services/rag_service.py`。

5. **LLM 调用与结构化输出**
   - 学：prompt 设计、JSON 解析、失败降级。
   - 在项目里读：`backend/services/llm_service.py`、`backend/services/generation_service.py`。

6. **LangChain / LangGraph**
   - 学：Message、Tool、StateGraph、ReAct。
   - 在项目里读：`backend/workflow/graph.py`、`backend/workflow/tools.py`、`backend/services/agent_service.py`。

### 第三优先级：前端工程

7. **Vue 3 组合式 API + TypeScript**
   - 学：setup 语法、ref/computed、组件通信。
   - 在项目里读：`frontend/src/views/AgentChatView.vue`。

8. **Pinia + Router + API 封装**
   - 学：状态管理、路由守卫、fetch 拦截器。
   - 在项目里读：`frontend/src/stores/auth.ts`、`frontend/src/api/client.ts`。

### 第四优先级：算法与测试

9. **FSRS / 间隔重复**
   - 学：记忆曲线、调度参数。
   - 在项目里读：`backend/services/fsrs_scheduler.py`。

10. **测试**
    - 学：pytest、mock、集成测试。
    - 在项目里读：`backend/tests/test_integration.py`、`backend/conftest.py`。

### 第五优先级：软件设计与架构

11. **设计模式**
    - 工厂模式（`parsers/factory.py`）
    - 依赖注入（FastAPI Depends）
    - 策略/适配器（embedding 抽象、LLMService 抽象）
    - 分层架构、防腐层（Agent 不直接 SQL）

12. **AI 系统设计**
    - 什么时候该用 Agent、什么时候该用 Pipeline
    - 怎么给 LLM 输出加护栏
    - 怎么设计“人机确认”机制

---

## 最后：如果这是你从零设计，怎么理解它？

从零设计思维链：

1. **先定义核心资产**：学习资料、知识树、题目、用户学习记录。
2. **再定义闭环**：资料 → 知识 → 题目 → 刷题 → 错题 → 复习 → 诊断。
3. **区分确定性与非确定性**：判题、FSRS、权限是确定性；理解意图、提取知识、出题是非确定性。
4. **把非确定性收敛到一个入口**：主 Agent 负责决策，专家内部固定流程。
5. **给 AI 加护栏**：写操作确认、三层校验、重试上限、熔断。
6. **最后才是技术选型**：FastAPI 做分层，LangGraph 做状态，Chroma 做检索，Vue 做 UI。

EStudy 最大的价值不是“用了 AI”，而是**把 AI 放进了一个有边界、可测试、可解释的工程系统里**。面试时能讲清楚这条边界，就已经超过大多数只会“调 API”的候选人了。
