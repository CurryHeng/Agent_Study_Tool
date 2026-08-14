
# EStudy 详细设计说明书

> 版本：V0.1
> 阶段：MVP / P0
> 目标：指导 Claude 等 AI 编程工具进行项目实现
> 原则：轻量、低成本、快速开发、保证核心功能质量

---

# 1. 详细设计原则

EStudy 采用以下实现原则：

1. **确定性任务优先使用普通程序完成**，非确定性的理解、生成、判断任务交给 Agent。
2. **Agent 不直接执行原始 SQL**，数据库操作通过受控 Tool 完成。
3. **Agent 之间通过结构化 State / JSON 传递信息**，避免依赖自然语言上下文。
4. **LangGraph 负责 Agent 工作流和状态管理**。
5. **RAG 作为公共能力服务**，不单独设计复杂的 RAG Agent。
6. P0 优先保证核心链路：

```text
资料导入
→ 文档解析
→ 知识提取
→ 思维导图
→ RAG
→ 自动出题
→ AI审题
→ 题库
→ 刷题
```

7. 所有 P1/P2 功能在结构上预留，但不影响 P0 开发。

---

# 2. Agent State 设计

## 2.1 设计目标

LangGraph 中所有 Agent 围绕一个统一的任务状态运行：

```text
TaskState
```

它是一次 Agent 任务执行过程中的共享数据。

例如用户输入：

> “根据这份高数资料生成20道选择题。”

State 会逐步变成：

```text
用户请求
 ↓
任务识别
 ↓
课程/文档信息
 ↓
知识点
 ↓
RAG上下文
 ↓
生成题目
 ↓
审核结果
 ↓
最终结果
```

---

## 2.2 TaskState

建议 P0 使用以下字段：

| 字段                | 类型          | 说明                   |
| ----------------- | ----------- | -------------------- |
| task_id           | string      | 当前任务唯一 ID            |
| user_id           | string      | 用户 ID                |
| course_id         | string/null | 当前课程                 |
| user_request      | string      | 用户原始请求               |
| intent            | string      | 用户意图                 |
| task_plan         | object/list | Orchestrator 生成的任务计划 |
| current_step      | string      | 当前执行节点               |
| document_ids      | list        | 涉及的文档                |
| knowledge_ids     | list        | 涉及的知识点               |
| retrieved_context | list        | RAG 检索结果             |
| generated_data    | object      | Agent 产生的业务数据        |
| review_result     | object/null | 审核结果                 |
| permission        | object      | 当前 Agent 操作权限        |
| errors            | list        | 错误记录                 |
| final_result      | object/null | 最终返回结果               |

---

## 2.3 State 简化结构

```text
TaskState
│
├── Identity
│   ├── task_id
│   ├── user_id
│   └── course_id
│
├── Request
│   ├── user_request
│   └── intent
│
├── Planning
│   ├── task_plan
│   └── current_step
│
├── Knowledge
│   ├── document_ids
│   ├── knowledge_ids
│   └── retrieved_context
│
├── AgentResult
│   ├── generated_data
│   └── review_result
│
├── Permission
│   └── permission
│
├── Error
│   └── errors
│
└── Result
    └── final_result
```

---

# 3. Agent State 使用规则

这里非常重要：

> **不是所有 Agent 都可以随意修改所有 State。**

建议采用以下约束：

| Agent           | 主要读取               | 主要修改                         |
| --------------- | ------------------ | ---------------------------- |
| Navigator       | Request、Knowledge  | intent、task_plan             |
| Orchestrator    | 全部                 | current_step、task_plan       |
| Document Agent  | document_ids       | generated_data               |
| Knowledge Agent | generated_data、RAG | knowledge_ids、generated_data |
| Question Agent  | knowledge、RAG      | generated_data               |
| Review Agent    | generated_data     | review_result                |
| RAG Service     | 检索参数               | retrieved_context            |

例如：

```text
Question Agent
    ↓
只负责生成题目
    ↓
不能直接修改 review_result
```

Review Agent：

```text
读取 generated_data
        ↓
进行审核
        ↓
写入 review_result
```

这样可以避免 Agent 之间互相覆盖数据。

---

# 4. Agent 输入输出协议

## 4.1 通用 AgentRequest

Agent 调用统一采用结构化请求：

```json
{
  "task_id": "task_xxx",
  "agent": "question_agent",
  "action": "generate_questions",
  "input": {},
  "context": {}
}
```

---

## 4.2 通用 AgentResponse

```json
{
  "task_id": "task_xxx",
  "agent": "question_agent",
  "status": "success",
  "data": {},
  "error": null
}
```

失败：

```json
{
  "task_id": "task_xxx",
  "agent": "question_agent",
  "status": "failed",
  "data": null,
  "error": {
    "code": "LLM_ERROR",
    "message": "模型调用失败"
  }
}
```

---

# 5. Navigator Agent 详细设计

## 输入

```text
user_request
user_id
course_id
当前页面/上下文
```

## 输出

```text
intent
task_plan
```

### 示例

用户：

> “根据第一章资料出十道选择题。”

Navigator 输出：

```json
{
  "intent": "generate_questions",
  "task_plan": {
    "type": "question_generation",
    "course_id": "course_001",
    "chapter": "第一章",
    "question_type": "single_choice",
    "count": 10
  }
}
```

Navigator **不直接调用 Question Agent**。

它只负责：

```text
理解
→ 结构化
→ 交给 Orchestrator
```

---

# 6. Orchestrator 详细设计

Orchestrator 使用 **LangGraph** 实现。

职责只有三个：

```text
任务规划
任务调度
任务状态控制
```

核心逻辑：

```text
Navigator
    ↓
TaskState
    ↓
Orchestrator
    ↓
判断下一节点
    ↓
调用 Agent
    ↓
检查结果
    ↓
下一节点 / 重试 / 结束
```

---

# 7. Question Agent 详细设计

## 输入

```text
course_id
knowledge_ids
question_type
count
difficulty
retrieved_context
```

## 输出

```text
generated_data.questions
```

题目统一结构：

```json
{
  "type": "single_choice",
  "content": "题目内容",
  "options": [
    "A. xxx",
    "B. xxx",
    "C. xxx",
    "D. xxx"
  ],
  "answer": "A",
  "analysis": "答案解析",
  "knowledge_id": "knowledge_xxx",
  "difficulty": 2
}
```

P0：

```text
single_choice
multiple_choice
true_false
fill_blank
```

---

# 8. Review Agent 详细设计

Review Agent 不负责重新生成题目，只负责审核。

检查：

```text
题目
│
├── 格式
├── 答案
├── 选项
├── 知识点匹配
├── 内容合理性
└── 难度合理性
```

输出：

```json
{
  "passed": true,
  "score": 0.92,
  "issues": []
}
```

如果失败：

```text
Question Agent
      ↓
Review Agent
      ↓
FAIL
      ↓
重新生成
```

**P0 设置最大重试次数，例如 2 次。**

避免：

```text
Question → Review → Question → Review → ...
```

无限循环。

---

# 9. Document Agent 详细设计

Document Agent 接收统一格式的解析结果。

因此文件解析器和 Agent 解耦：

```text
PDF Parser ──┐
Word Parser ─┤
PPT Parser ──┼→ Document Representation
MD Parser ───┤
Image/OCR ───┘
                    ↓
              Document Agent
```

Document Agent 不关心原始文件格式。

---

# 10. Document Representation

这是整个文档系统非常重要的中间结构。

建议统一为：

```text
Document
│
├── id
├── title
├── source_type
├── metadata
└── sections[]
      │
      ├── title
      ├── level
      ├── paragraphs[]
      ├── tables[]
      └── images[]
```

例如：

```json
{
  "id": "doc_001",
  "title": "高等数学期末复习提纲",
  "source_type": "pdf",
  "sections": [
    {
      "title": "第一章 函数与极限",
      "level": 1,
      "paragraphs": [
        "函数的定义……",
        "极限的定义……"
      ]
    }
  ]
}
```

这样以后增加 Excel、网页、扫描 PDF 等格式，也不会影响 Agent 层。

---

# 11. Knowledge Agent 详细设计

输入：

```text
Document Representation
+
RAG Context
```

输出：

```text
Knowledge Tree
```

结构：

```text
Knowledge
│
├── id
├── name
├── description
├── parent_id
├── level
└── source_document_id
```

最终形成：

```text
高等数学
├── 函数与极限
│   ├── 函数
│   ├── 极限
│   └── 连续
└── 导数
    ├── 导数定义
    └── 导数应用
```

这个结构同时服务：

```text
思维导图
RAG metadata
出题
课程知识浏览
```

---

# 12. RAG 详细设计

P0 的主要用途：

> **为 Question Agent 提供课程资料上下文。**

流程：

```text
Document
   ↓
Chunk
   ↓
Embedding
   ↓
Chroma
```

出题：

```text
Knowledge
   ↓
Retriever
   ↓
Chroma
   ↓
Top-K Context
   ↓
Question Agent
```

Metadata 至少包含：

```json
{
  "course_id": "course_001",
  "document_id": "doc_001",
  "section": "第一章",
  "knowledge_id": "knowledge_001"
}
```

这样可以进行：

```text
course_id filter
+
knowledge_id filter
```

避免检索到其他课程的内容。

---

# 13. Tool 设计

Agent 不直接操作数据库。

Agent 通过 Tool 操作系统。

例如：

```text
Tools
│
├── search_knowledge()
├── search_documents()
├── create_question()
├── update_question()
├── delete_question()
├── create_mindmap()
└── get_course_info()
```

执行链：

```text
Agent
 ↓
Tool
 ↓
Permission
 ↓
Service
 ↓
Repository
 ↓
Database
```

---

# 14. Agent 权限设计

默认：

> **只读 + 新增**

涉及：

```text
修改
删除
批量操作
```

时需要额外权限。

可以设计为：

```text
Permission
│
├── read
├── create
├── update
└── delete
```

例如：

```text
用户关闭 AI 修改权限
        ↓
Agent 请求 update_question()
        ↓
Permission Check
        ↓
拒绝
        ↓
提示用户开启权限
```

开启权限后才允许执行。

---

# 15. 思维导图数据设计

P0 不保存成图片，而保存为结构化数据。

```json
{
  "root": {
    "id": "root",
    "label": "高等数学",
    "children": [
      {
        "id": "k001",
        "label": "函数与极限",
        "children": []
      }
    ]
  }
}
```

这样：

```text
P0 → 查看
P1 → 手动编辑
P2 → AI修改
```

全部可以复用同一数据结构。

---

# 16. 当前详细设计的核心关系

最终把整个 Agent 系统理解成：

```text
                  用户
                   │
                   ▼
              Navigator
                   │
              TaskState
                   │
                   ▼
             Orchestrator
              LangGraph
                   │
       ┌───────────┼───────────┐
       ▼           ▼           ▼
   Document    Knowledge    Question
      Agent       Agent        Agent
                                  │
                                  ▼
                             Review Agent
                                  │
                                  ▼
                              TaskState
                                  │
                                  ▼
                               用户
```

而数据能力在下面：

```text
                Agents
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
       Tools      RAG       LLM
        │          │          │
        ▼          ▼          ▼
     Service    Chroma     DeepSeek
        │
        ▼
     SQLite
```

---

# 17. 给 Claude 的开发约束

这一部分我建议**单独保留**，以后直接丢给 Claude 很有用。

### EStudy 开发约束

```text
1. 不要擅自引入微服务、Redis、消息队列等重量级组件。

2. Agent 使用 LangGraph 管理工作流。

3. Navigator 与 Orchestrator 必须保持职责分离。

4. Agent 之间优先通过结构化 State/JSON 传递数据。

5. Agent 不直接执行 SQL。

6. 数据库操作必须经过 Tool → Service → Repository。

7. RAG 作为公共服务能力，不单独设计复杂 RAG Agent。

8. SQLite 保存业务数据，Chroma 保存向量数据。

9. 确定性逻辑优先使用普通程序实现，避免无意义的 LLM 调用。

10. LLM 输出必须进行结构化解析和校验，不能默认可信。

11. Question Agent 生成题目后必须经过 Review Agent。

12. Review 失败最多自动重试 2 次。

13. P0 功能优先，不为了未来功能提前实现复杂系统。

14. P1/P2 功能可以预留接口，但不能阻塞 P0。

15. 优先保证代码简单、模块清晰、方便调试。
```
