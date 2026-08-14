

```text
详细设计说明书
├── 1. Agent架构与交互设计        ← 已完成
├── 2. LangGraph工作流设计        ← 本次
├── 3. 文档解析详细设计
├── 4. RAG详细设计
├── 5. 数据库详细设计
├── 6. 后端API详细设计
├── 7. 前端详细设计
├── 8. 权限与异常处理设计
└── 9. 项目代码结构设计
```


# EStudy 详细设计说明书

## 2. LangGraph 工作流详细设计

### 2.1 工作流总体结构

EStudy 使用 LangGraph 管理 Agent 的执行流程。

核心流程：

```text
START
  ↓
Navigator
  ↓
Orchestrator
  ↓
Task Router
  ├── Document Agent
  ├── Knowledge Agent
  ├── Question Agent
  └── Other Agent
          ↓
      Review Agent
          ↓
     Result Handler
          ↓
         END
```

Navigator 负责理解用户意图，Orchestrator 负责根据任务计划调度具体 Agent。

---

### 2.2 Navigator 流程

```text
用户输入
   ↓
Navigator
   ↓
意图识别
   ↓
生成结构化任务
   ↓
写入 TaskState
   ↓
Orchestrator
```

Navigator 不直接决定具体 Agent 的执行顺序。

例如：

```text
用户：
“根据第一章生成10道选择题”

Navigator：
intent = generate_questions

task_plan：
document → knowledge → rag → question → review
```

---

### 2.3 Orchestrator 流程

Orchestrator 根据 `TaskState.task_plan` 决定下一执行节点。

```text
                Orchestrator
                     │
                     ▼
                 Task Router
                     │
       ┌─────────────┼─────────────┐
       ▼             ▼             ▼
   Document      Knowledge      Question
       │             │             │
       └─────────────┼─────────────┘
                     ▼
                  Review
                     │
              ┌──────┴──────┐
              ▼             ▼
            PASS           FAIL
              │             │
              ▼             ▼
            Result       Retry
                            │
                            └──→ Question
```

---

### 2.4 Question 生成工作流

P0 最重要的 Agent 工作流：

```text
用户请求
 ↓
Navigator
 ↓
Orchestrator
 ↓
获取课程/知识点
 ↓
RAG检索
 ↓
Question Agent
 ↓
题目格式校验
 ↓
Review Agent
 ↓
审核通过？
 ├── 是 → 保存题目 → 返回用户
 └── 否 → 重新生成
              ↓
          最大2次
              ↓
          仍失败 → 返回异常
```

---

### 2.5 文档导入工作流

```text
上传文件
 ↓
文件校验
 ↓
格式识别
 ↓
对应 Parser
 ↓
统一 Document Representation
 ↓
Document Agent
 ↓
知识提取
 ↓
生成知识树
 ↓
生成思维导图
 ↓
Chunk
 ↓
Embedding
 ↓
写入 Chroma
 ↓
保存数据库
```

文档解析和 Agent 处理分离。

```text
Parser
```

负责：

> “把文件变成可处理的数据。”

```text
Document Agent
```

负责：

> “理解这些数据是什么。”

---

## 3. 文档解析详细设计

### 3.1 支持格式

P0 支持：

```text
PDF
Markdown
Word
PPT
图片
```

统一进入：

```text
Document Representation
```

---

### 3.2 Parser 设计

```text
Parser
│
├── PDFParser
├── MarkdownParser
├── WordParser
├── PPTParser
└── ImageParser
```

统一接口：

```text
parse(file) → Document
```

这样后续增加新的格式时，只需要增加 Parser，不修改 Agent。

---

### 3.3 图片解析

图片主要用于：

* 扫描版资料
* 教材截图
* 手写/打印提纲
* 图片中的题目

流程：

```text
Image
 ↓
Vision Model
 ↓
OCR / 内容理解
 ↓
Document Representation
```

图片解析优先使用千问视觉模型。

---

### 3.4 文件校验

上传时先进行：

```text
文件存在性检查
 ↓
格式检查
 ↓
文件大小检查
 ↓
解析
```

网站部署时增加：

```text
解析超时
并发限制
用户存储限制
```

这些参数统一由配置文件管理。

---

## 4. RAG 详细设计

### 4.1 RAG 数据流程

```text
Document
 ↓
Text Extraction
 ↓
Chunk
 ↓
Embedding
 ↓
Chroma
```

查询：

```text
Query
 ↓
Embedding
 ↓
Similarity Search
 ↓
Metadata Filter
 ↓
Top-K Context
 ↓
Agent
```

---

### 4.2 Chunk

P0 使用简单的结构化切分策略：

```text
章节
 ↓
段落
 ↓
固定长度 Chunk
```

优先保证：

> 不破坏原文语义和章节关系。

每个 Chunk 保存：

```text
chunk_id
course_id
document_id
section
knowledge_id
content
```

---

### 4.3 检索

默认检索：

```text
Top-K
+
course_id
+
knowledge_id
```

例如用户要求：

> 根据“极限”出题。

检索范围：

```text
course_id = 当前课程
knowledge_id = 极限
```

避免不同课程之间发生知识污染。

---

### 4.4 RAG 服务接口

RAG 对 Agent 提供统一接口：

```text
retrieve(
    query,
    course_id,
    knowledge_id,
    top_k
)
```

返回：

```text
[
    {
        chunk_id,
        content,
        metadata,
        score
    }
]
```

Question Agent 不直接操作 Chroma。

---

# 5. 数据库详细设计

## 5.1 数据库组成

```text
SQLite
│
├── users
├── courses
├── documents
├── knowledge
├── mindmaps
├── questions
├── question_options
├── answer_records
├── wrong_questions
└── agent_tasks
```

---

## 5.2 User

| 字段            | 类型       | 说明   |
| ------------- | -------- | ---- |
| id            | INTEGER  | 主键   |
| username      | TEXT     | 用户名  |
| password_hash | TEXT     | 密码摘要 |
| created_at    | DATETIME | 创建时间 |

---

## 5.3 Course

| 字段          | 类型       | 说明   |
| ----------- | -------- | ---- |
| id          | INTEGER  | 主键   |
| user_id     | INTEGER  | 所属用户 |
| name        | TEXT     | 课程名称 |
| description | TEXT     | 描述   |
| created_at  | DATETIME | 创建时间 |

---

## 5.4 Document

| 字段         | 类型       | 说明   |
| ---------- | -------- | ---- |
| id         | INTEGER  | 主键   |
| course_id  | INTEGER  | 所属课程 |
| filename   | TEXT     | 原文件名 |
| file_type  | TEXT     | 文件类型 |
| file_path  | TEXT     | 文件路径 |
| status     | TEXT     | 解析状态 |
| created_at | DATETIME | 创建时间 |

状态：

```text
pending
processing
success
failed
```

---

## 5.5 Knowledge

| 字段          | 类型      | 说明    |
| ----------- | ------- | ----- |
| id          | INTEGER | 主键    |
| course_id   | INTEGER | 所属课程  |
| document_id | INTEGER | 来源文档  |
| parent_id   | INTEGER | 父知识点  |
| name        | TEXT    | 知识点名称 |
| description | TEXT    | 知识点描述 |
| level       | INTEGER | 层级    |

`parent_id` 用于构建知识树。

---

## 5.6 MindMap

| 字段         | 类型        | 说明     |
| ---------- | --------- | ------ |
| id         | INTEGER   | 主键     |
| course_id  | INTEGER   | 所属课程   |
| data       | JSON/TEXT | 思维导图结构 |
| version    | INTEGER   | 版本     |
| created_at | DATETIME  | 创建时间   |

P0 直接保存结构化 JSON。

---

## 5.7 Question

| 字段           | 类型      | 说明   |
| ------------ | ------- | ---- |
| id           | INTEGER | 主键   |
| course_id    | INTEGER | 所属课程 |
| knowledge_id | INTEGER | 知识点  |
| type         | TEXT    | 题型   |
| content      | TEXT    | 题目   |
| answer       | TEXT    | 答案   |
| analysis     | TEXT    | 解析   |
| difficulty   | INTEGER | 难度   |
| source       | TEXT    | 来源   |
| status       | TEXT    | 状态   |

---

## 5.8 QuestionOption

主要用于选择题：

| 字段          | 类型      | 说明      |
| ----------- | ------- | ------- |
| id          | INTEGER | 主键      |
| question_id | INTEGER | 题目      |
| label       | TEXT    | A/B/C/D |
| content     | TEXT    | 选项内容    |

---

## 5.9 AnswerRecord

记录用户答题：

```text
id
user_id
question_id
user_answer
is_correct
created_at
```

---

## 5.10 WrongQuestion

记录错题：

```text
id
user_id
question_id
wrong_count
last_wrong_at
```

后续可以进一步扩展错因分析。

---

## 5.11 AgentTask

用于记录 Agent 任务：

```text
id
user_id
task_type
status
input_data
result_data
error_message
created_at
finished_at
```

状态：

```text
pending
running
success
failed
cancelled
```

这个表对于调试 Agent 非常重要。

---

# 6. 后端 API 详细设计

API 采用 REST 风格。

## 6.1 用户

```text
POST /api/auth/register
POST /api/auth/login
```

---

## 6.2 课程

```text
GET    /api/courses
POST   /api/courses
GET    /api/courses/{id}
DELETE /api/courses/{id}
```

---

## 6.3 文档

```text
POST /api/documents/upload
GET  /api/documents/{id}
DELETE /api/documents/{id}
```

上传后：

```text
upload
 ↓
parse
 ↓
knowledge
 ↓
mindmap
 ↓
rag
```

---

## 6.4 知识

```text
GET /api/courses/{id}/knowledge
GET /api/knowledge/{id}
```

---

## 6.5 思维导图

```text
GET /api/courses/{id}/mindmap
PUT /api/courses/{id}/mindmap
```

P0 主要使用 GET。

PUT 为后续编辑功能预留。

---

## 6.6 题库

```text
GET    /api/questions
POST   /api/questions/generate
GET    /api/questions/{id}
PUT    /api/questions/{id}
DELETE /api/questions/{id}
```

---

## 6.7 刷题

```text
POST /api/exams/start
POST /api/questions/{id}/answer
GET  /api/exams/{id}/result
```

---

## 6.8 AI 助手

核心接口：

```text
POST /api/agent/chat
```

请求：

```json
{
  "message": "根据第一章生成10道选择题",
  "course_id": 1
}
```

响应：

```json
{
  "task_id": "task_xxx",
  "status": "success",
  "message": "已生成10道题",
  "data": {}
}
```

---

# 7. 前端详细设计

## 7.1 页面结构

```text
EStudy
│
├── 登录
├── 注册
│
├── 首页
│
├── 课程
│   ├── 资料
│   ├── 知识点
│   ├── 思维导图
│   ├── 题库
│   └── 错题
│
├── 刷题
│
└── AI助手
```

---

## 7.2 AI 助手

采用全局入口：

```text
┌────────────────────────────┐
│       当前学习内容          │
│                            │
│                            │
│                       ┌────┤
│                       │ AI │
│                       │助手│
│                       └────┤
└────────────────────────────┘
```

用户可以直接输入：

> “帮我出题。”

> “解释这个知识点。”

> “帮我整理第一章。”

> “删除刚刚生成的题。”

---

# 8. 权限与异常设计

## 8.1 Agent 权限

分为：

```text
READ
CREATE
UPDATE
DELETE
```

默认：

```text
READ + CREATE
```

UPDATE / DELETE 需要用户授权。

---

## 8.2 LLM 异常

包括：

```text
API调用失败
超时
返回格式错误
Token超限
```

处理：

```text
第一次失败
 ↓
自动重试
 ↓
仍失败
 ↓
返回任务失败
```

---

## 8.3 Agent 异常

Agent 节点失败时：

```text
Node
 ↓
Exception Handler
 ↓
Retry
 ↓
仍失败
 ↓
TaskState.errors
 ↓
Result Handler
```

---

## 8.4 JSON 校验

LLM 输出不能直接写数据库。

必须：

```text
LLM
 ↓
JSON Parse
 ↓
Schema Validate
 ↓
Business Validate
 ↓
Database
```

例如题目：

```text
LLM生成
 ↓
是否有answer？
 ↓
选项数量是否正确？
 ↓
answer是否存在？
 ↓
knowledge_id是否有效？
 ↓
保存
```

---

# 9. 项目代码结构设计

为了让 Claude 后续比较容易理解，我建议最终代码结构保持简单：

```text
EStudy/
│
├── frontend/
│   └── src/
│
├── backend/
│   │
│   ├── main.py
│   │
│   ├── api/
│   │   ├── auth.py
│   │   ├── courses.py
│   │   ├── documents.py
│   │   ├── questions.py
│   │   └── agent.py
│   │
│   ├── agents/
│   │   ├── navigator.py
│   │   ├── orchestrator.py
│   │   ├── document_agent.py
│   │   ├── knowledge_agent.py
│   │   ├── question_agent.py
│   │   └── review_agent.py
│   │
│   ├── workflow/
│   │   ├── graph.py
│   │   └── state.py
│   │
│   ├── rag/
│   │   ├── chunker.py
│   │   ├── embedding.py
│   │   ├── retriever.py
│   │   └── chroma.py
│   │
│   ├── parsers/
│   │   ├── pdf.py
│   │   ├── markdown.py
│   │   ├── word.py
│   │   ├── ppt.py
│   │   └── image.py
│   │
│   ├── tools/
│   │   ├── knowledge_tools.py
│   │   ├── question_tools.py
│   │   └── document_tools.py
│   │
│   ├── services/
│   │   ├── course_service.py
│   │   ├── document_service.py
│   │   ├── question_service.py
│   │   └── agent_service.py
│   │
│   ├── models/
│   │   ├── user.py
│   │   ├── course.py
│   │   ├── document.py
│   │   ├── knowledge.py
│   │   └── question.py
│   │
│   ├── repositories/
│   │   └── ...
│   │
│   └── config.py
│
├── data/
│   ├── uploads/
│   └── chroma/
│
├── tests/
│
└── README.md
```

---

# 10. P0 实现优先级

为了确保 15 天能完成，不建议按照目录顺序开发，而是按照**最小闭环**开发。

### 第一阶段：基础框架

```text
FastAPI
Vue
SQLite
LangGraph
DeepSeek
Chroma
```

↓

### 第二阶段：资料闭环

```text
上传
 ↓
解析
 ↓
知识点
 ↓
思维导图
```

↓

### 第三阶段：出题闭环

```text
RAG
 ↓
Question Agent
 ↓
Review Agent
 ↓
题库
```

↓

### 第四阶段：学习闭环

```text
刷题
 ↓
判题
 ↓
错题
```

↓

### 第五阶段：Navigator

```text
用户
 ↓
Navigator
 ↓
Orchestrator
 ↓
上述功能
```

这样即使开发过程中时间不足，也能够保证：

> **至少存在一个完整可演示的 AI 学习闭环。**

---

# 11. 详细设计完成后的整体关系

最终 EStudy 可以浓缩成这一张“开发视图”：

```text
                         EStudy
                           │
             ┌─────────────┴─────────────┐
             │                           │
           Vue                        FastAPI
                                         │
                                  Navigator Agent
                                         │
                                   LangGraph
                                  Orchestrator
                                         │
                 ┌───────────────────────┼──────────────────────┐
                 │                       │                      │
                 ▼                       ▼                      ▼
          Document Agent          Knowledge Agent        Question Agent
                 │                       │                      │
                 │                       │                 Review Agent
                 │                       │                      │
                 └───────────────┬───────┴──────────────────────┘
                                 │
                            RAG Service
                                 │
                            ┌────┴────┐
                            ▼         ▼
                         Chroma    DeepSeek
                                 
                  Tools → Services → Repository
                                 │
                              SQLite
```

这份已经基本覆盖了**详细设计阶段真正需要给开发人员的核心内容**。

其中数据库字段、API 参数、LangGraph 节点这些后面在真正编码时还可以继续细化，但现在**没必要为了写文档而把每个字段和接口写到几十页**。对你们这个 15 天 P0 的项目来说，这样的粒度更合适。
