---
name: langgraph
description: EStudy 的 LangGraph Agent 工作流开发规范。当编写/修改 Agent、LangGraph 图节点、TaskState、Orchestrator、Navigator 时加载。
---

# langgraph — LangGraph Agent 工作流开发规范

## 用途
指导 LangGraph 工作流与各 Agent 的实现，确保遵守 docs 确定的 State 读写权限、审题重试与输出校验约束。

## 何时加载
- 编写/修改 `backend/agents/*`（navigator/orchestrator/document_agent/knowledge_agent/question_agent/review_agent）
- 编写/修改 `backend/workflow/*`（graph.py / state.py）
- 涉及 LLM 调用、题目生成/审核、任务规划时

## 必须遵守的规范

### 1. 架构（硬约束）
```
用户 → Navigator Agent → Orchestrator（LangGraph）→ Document/Knowledge/Question Agent → Review Agent → 用户
```
- **Navigator 与 Orchestrator 职责分离**：Navigator 回答「用户想做什么」（intent + task_plan），Orchestrator 回答「怎么完成」（调度/状态）。
- Navigator 不直接调用专业 Agent。

### 2. TaskState（统一状态）
字段：`task_id, user_id, course_id, user_request, intent, task_plan, current_step, document_ids, knowledge_ids, retrieved_context, generated_data, review_result, permission, errors, final_result`

### 3. State 读写权限（各 Agent 只能写自己职责）
| Agent | 写 | 读 |
|---|---|---|
| Navigator | intent, task_plan | Request, Knowledge |
| Orchestrator | current_step, task_plan | 全部 |
| Document | generated_data | document_ids |
| Knowledge | knowledge_ids, generated_data | generated_data, RAG |
| Question | generated_data | knowledge, RAG |
| Review | review_result | generated_data |

### 4. 工作流控制
- 主流程：`START → Navigator → Orchestrator → Task Router → 专业 Agent → Review → Result Handler → END`。
- Review **FAIL 循环回 Question Agent**，**最大重试 2 次**，仍失败返回异常（禁止无限循环）。
- 简单咨询任务由 Navigator 直接回答，不进图。

### 5. LLM 调用与校验（硬约束）
- 所有模型调用统一经 `LLMService`，Agent **不直接 import 模型 SDK**。
- Agent 间通过结构化 State/JSON 传递，不依赖自然语言上下文。
- 重要输出入库前必须过**三层校验**：① 格式（合法 JSON）② 结构（必需字段）③ 业务（如选项数=4、答案对应选项、knowledge_id 有效、difficulty 范围）。
- 长文档先 RAG 检索，只把相关内容交给 LLM，禁止整篇塞入。

### 6. 权限
- Agent 默认 `read + create`；`update/delete/批量` 需额外授权。
- 禁止 `LLM → 任意 SQL / 任意文件操作 / 任意系统命令`。

### 参考
- docs：`详细设计.md`（§2-4 Agent/工具/专家、§9 错误处理、§10 测试）。
