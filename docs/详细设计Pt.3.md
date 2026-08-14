# 12. 系统接口与模块协作设计

## 12.1 模块调用关系

EStudy 后端模块遵循以下调用方向：

```text
API
 ↓
Service
 ↓
Repository
 ↓
Database
```

Agent 相关：

```text
API
 ↓
Agent Service
 ↓
Navigator
 ↓
Orchestrator
 ↓
专业 Agent
 ↓
Tools / RAG / LLM
 ↓
Service
 ↓
Repository
```

原则：

> 上层可以调用下层，下层不主动依赖上层。

例如：

```text
Question Agent
```

可以调用：

```text
Question Tool
```

但不能直接调用：

```text
FastAPI Route
```

---

## 12.2 文档导入模块协作

```text
Frontend
   ↓
Document API
   ↓
Document Service
   ↓
Parser Factory
   ↓
┌──────┬──────┬──────┬──────┐
PDF   MD    Word    PPT   Image
Parser Parser Parser Parser Parser
   └──────┴──────┴──────┴──────┘
                ↓
     Document Representation
                ↓
        Document Agent
                ↓
        Knowledge Agent
                ↓
        MindMap + RAG
```

---

## 12.3 出题模块协作

```text
Navigator
    ↓
Orchestrator
    ↓
RAG
    ↓
Question Agent
    ↓
Schema Validation
    ↓
Review Agent
    ↓
Business Validation
    ↓
Question Service
    ↓
SQLite
```

---

# 13. 数据流设计

这一部分主要描述**数据怎么流动**，不再重复功能需求。

---

## 13.1 文件数据流

```text
用户文件
 ↓
Upload
 ↓
临时文件
 ↓
Parser
 ↓
Document Representation
 ↓
SQLite保存文档信息
 ↓
Knowledge Agent
 ↓
Knowledge Tree
 ↓
MindMap
 ↓
Chunk
 ↓
Embedding
 ↓
Chroma
```

---

## 13.2 出题数据流

```text
用户请求
 ↓
Navigator
 ↓
TaskState
 ↓
Orchestrator
 ↓
Knowledge
 ↓
RAG Retrieval
 ↓
Context
 ↓
Question Agent
 ↓
Question JSON
 ↓
Review Agent
 ↓
通过
 ↓
Question Service
 ↓
SQLite
```

---

## 13.3 刷题数据流

```text
用户开始刷题
 ↓
获取题目
 ↓
用户提交答案
 ↓
Answer Service
 ↓
程序判题
 ↓
AnswerRecord
 ↓
判断是否错误
 ├── 正确 → 记录答题
 └── 错误 → WrongQuestion
```

P0 不使用 LLM 判断选择题、判断题。

---

# 14. 状态与生命周期设计

## 14.1 文档生命周期

```text
UPLOADED
   ↓
PROCESSING
   ↓
PARSED
   ↓
ANALYZING
   ↓
COMPLETED
```

失败：

```text
PROCESSING
   ↓
FAILED
```

---

## 14.2 Agent Task 生命周期

```text
PENDING
   ↓
RUNNING
   ↓
SUCCESS
```

异常：

```text
RUNNING
   ↓
RETRYING
   ↓
SUCCESS / FAILED
```

---

## 14.3 题目生命周期

建议：

```text
GENERATED
   ↓
REVIEWING
   ↓
APPROVED
```

审核失败：

```text
REJECTED
   ↓
REGENERATING
```

最终：

```text
APPROVED → AVAILABLE
```

这样以后可以区分：

> AI 刚生成的题目

和：

> 已经过审核、可以进入正式题库的题目。

---

# 15. AI 输出质量控制设计

这是 EStudy 比普通 CRUD 项目更需要注意的一部分。

## 15.1 三层校验

所有重要 Agent 输出遵循：

```text
LLM
 ↓
① 格式校验
 ↓
② 结构校验
 ↓
③ 业务校验
 ↓
Database
```

---

### 第一层：格式校验

例如要求：

```json
{
  "questions": []
}
```

如果模型返回普通文本：

```text
“好的，我来为你生成题目……”
```

直接判定失败。

---

### 第二层：结构校验

检查：

```text
questions 是否存在
content 是否存在
answer 是否存在
type 是否正确
```

---

### 第三层：业务校验

例如选择题：

```text
选项数量 = 4
答案必须存在
答案必须对应选项
knowledge_id 必须有效
difficulty 范围正确
```

---

# 16. LLM 调用设计

为了控制速度和成本，统一封装：

```text
LLMService
```

Agent 不直接调用 DeepSeek SDK。

调用关系：

```text
Agent
 ↓
LLMService
 ↓
Model Provider
 ↓
DeepSeek
```

以后如果更换模型：

```text
DeepSeek
 ↓
其他模型
```

不需要修改 Agent。

---

## 16.1 模型用途

当前：

|模型|用途|
|---|---|
|DeepSeek|文本理解、知识提取、题目生成、审核、Navigator|
|千问视觉模型|图片理解、OCR、复杂视觉内容解析|

---

## 16.2 Token 控制

对于长文档：

```text
原始文档
 ↓
Chunk
 ↓
检索
 ↓
只把相关内容交给 LLM
```

不要：

```text
整个 PDF
 ↓
直接塞给 Question Agent
```

这样可以同时降低：

- Token 消耗
    
- 响应时间
    
- 上下文干扰
    

---

# 17. 日志与调试设计

由于 EStudy 大量使用 Agent，普通日志不足以定位问题。

因此 Agent 任务至少记录：

```text
task_id
user_id
agent_name
node_name
start_time
end_time
status
error
```

开发阶段可以额外记录：

```text
input
output
```

但正式网站部署时需要注意隐私和 Token 成本。

---

## 17.1 Agent 调试链

出现问题时能够追踪：

```text
task_001
 ↓
Navigator
 ↓
Orchestrator
 ↓
Question Agent
 ↓
Review Agent
 ↓
FAILED
```

而不是只看到：

```text
“AI生成失败”
```

---

# 18. 配置管理设计

不要把 API Key、模型参数写死在代码中。

统一使用：

```text
.env
```

例如：

```text
DEEPSEEK_API_KEY=
QWEN_API_KEY=

LLM_MODEL=
EMBEDDING_MODEL=

DATABASE_URL=
CHROMA_PATH=

MAX_FILE_SIZE=
MAX_RETRY=
```

代码通过：

```text
config.py
```

读取。

---

## 18.1 开发环境与生产环境

预留：

```text
.env.development
.env.production
```

本地开发：

```text
SQLite
Chroma
本地文件
```

未来网站：

```text
SQLite / 云数据库
Chroma / 云向量数据库
对象存储
```

尽量不修改业务层代码。

---

# 19. 安全设计

MVP 阶段不做复杂安全系统，但保留几个基本要求。

### 用户

```text
密码
 ↓
Hash
 ↓
数据库
```

不保存明文密码。

### 文件

上传文件必须检查：

```text
扩展名
MIME类型
大小
```

### Agent

禁止：

```text
LLM → 任意SQL
LLM → 任意文件系统操作
LLM → 任意系统命令
```

所有高风险操作必须经过 Tool。

---

# 20. 测试设计

这里也不需要做得过重。

## 20.1 单元测试

优先测试：

```text
Parser
Chunker
RAG Retriever
Question Validator
Answer Checker
Permission Checker
```

这些都是确定性逻辑。

---

## 20.2 Agent 测试

Agent 不要求每次输出完全一致，因此重点测试：

```text
输入
 ↓
Agent
 ↓
输出结构是否正确
```

例如：

```text
Question Agent
 ↓
是否产生10道题
 ↓
题型是否正确
 ↓
每题是否存在答案
```

而不是比较完整字符串。

---

## 20.3 核心流程测试

P0 至少保证三条：

### 测试一：资料导入

```text
PDF
 ↓
解析
 ↓
知识点
 ↓
思维导图
 ↓
RAG
```

### 测试二：AI 出题

```text
资料
 ↓
RAG
 ↓
Question Agent
 ↓
Review Agent
 ↓
题库
```

### 测试三：刷题

```text
题库
 ↓
答题
 ↓
判题
 ↓
错题
```

---

# 21. MVP 验收标准

这个文档建议单独留着，因为你们只有 **15 天 P0**，必须防止开发过程中不断加需求。

## P0 必须满足

> 状态标记：✅ 已完成 / 🟡 部分或简化实现 / ⬜ 未实现（后置）

### 文件

-  PDF 导入 ✅
-  Markdown 导入 ✅
-  Word 导入 ✅
-  PPT 导入 ✅
-  图片导入 ⬜（P1，需千问视觉）
-  文件解析成功率达到可接受水平 ✅

### 知识

-  自动提取知识点 ✅（确定性 `import_sections`；LLM 语义提取后置）
-  自动生成思维导图 ✅
-  思维导图可查看 ✅

### AI

-  Navigator ✅
-  Orchestrator ✅
-  Document Agent 🟡（节点存在，语义理解后置）
-  Knowledge Agent 🟡（确定性实现）
-  Question Agent ✅
-  Review Agent ✅

### 题库

-  选择题 ✅
-  判断题 ✅
-  填空题 ✅
-  自动判题 ✅
-  错题记录 ✅

### 基础系统

-  注册 ✅
-  登录 ✅
-  课程（=练习册 Workbook）✅
-  SQLite ✅
-  Chroma ✅

---

# 22. P1 / P2 扩展接口

为了避免以后重新设计，当前只保留接口。

> 实现进度：P1/P2 均未实现，仅保留方向。
> 已有雏形：`LearningAnalysis` → `GET /api/stats`；`QuestionFilter` → 题库搜索（前端）；简答题评分见下方 `AnswerEvaluationAgent`（未实现）。

## P1

```text
MindMapEditor
KnowledgeQA
AdvancedRAG
QuestionFilter
DifficultyControl
LearningAnalysis
```

---

## P2

```text
AnswerEvaluationAgent
LearningPlanAgent
TutorAgent
MindMapEditAgent
PersonalizedLearningAgent
```

尤其是简答题：

```text
Question Agent
      ↓
生成简答题
      ↓
Answer Evaluation Agent
      ↓
评分
      ↓
错因分析
```

现在只预留接口，不实现。

---

# 23. 开发顺序建议

最后这份最重要，因为它可以直接作为 Claude 的开发任务拆分。

## Phase 1：基础框架

```text
FastAPI
Vue
SQLite
SQLAlchemy/ORM
LangGraph
Chroma
LLMService
```

↓

## Phase 2：文件系统

```text
Upload
 ↓
Parser
 ↓
Document
```

↓

## Phase 3：知识系统

```text
Document
 ↓
Knowledge Agent
 ↓
Knowledge Tree
 ↓
MindMap
```

↓

## Phase 4：RAG

```text
Chunk
 ↓
Embedding
 ↓
Chroma
 ↓
Retriever
```

↓

## Phase 5：题库 Agent

```text
Question Agent
 ↓
Review Agent
 ↓
Question Service
```

↓

## Phase 6：刷题

```text
Exam
 ↓
Answer
 ↓
Judge
 ↓
Wrong Question
```

↓

## Phase 7：Navigator

```text
Navigator
 ↓
Orchestrator
 ↓
全部能力
```

↓

## Phase 8：UI 优化 + 测试

---

# 24. Claude 开发时的任务拆分原则

后续如果让 Claude Code / Claude 来实际开发，不建议直接说：

> “帮我把 EStudy 做出来。”

而应该拆成：

```text
Task 1
建立 FastAPI 项目骨架

Task 2
建立 SQLite 数据模型

Task 3
实现 PDF/MD/Word/PPT/Image Parser

Task 4
实现 Document Representation

Task 5
实现 Knowledge Agent

Task 6
实现 MindMap

Task 7
实现 Chroma RAG

Task 8
实现 Question Agent

Task 9
实现 Review Agent

Task 10
实现 Navigator + Orchestrator

Task 11
实现刷题系统

Task 12
前后端联调

Task 13
P0 测试
```

每完成一个任务再进入下一个。

---

# 25. 当前详细设计文档体系

至此，我们可以把详细设计阶段整理成：

```text
EStudy/
└── 详细设计
    │
    ├── 01-Agent架构与交互设计       ✓
    ├── 02-LangGraph工作流设计       ✓
    ├── 03-文档解析详细设计          ✓
    ├── 04-RAG详细设计               ✓
    ├── 05-数据库详细设计             ✓
    ├── 06-后端API详细设计            ✓
    ├── 07-前端详细设计               ✓
    ├── 08-权限与异常设计             ✓
    ├── 09-模块协作与数据流设计       ✓
    ├── 10-AI质量控制与LLM设计       ✓
    ├── 11-日志/配置/安全设计         ✓
    ├── 12-测试设计                   ✓
    └── 13-MVP验收与开发计划          ✓
```

