---
name: database
description: EStudy 数据库（SQLite + SQLAlchemy 2.0）开发规范。当定义/修改数据表、编写 Repository、设计实体关系、处理数据迁移时加载。
---

# database — SQLite + SQLAlchemy 2.0 开发规范

## 用途
指导数据库建模与数据访问，确保 SQLite 业务库与 Chroma 向量库分工清晰、分层合规。

## 何时加载
- 定义/修改 `backend/models/*`（SQLAlchemy 模型）
- 编写 `backend/repositories/*`
- 设计实体关系、状态机、迁移脚本

## 必须遵守的规范

### 1. 存储分工
- **SQLite**：结构化业务数据。
- **Chroma**：向量检索数据（chunk + embedding）。
- 两者职责分离，Agent 不得直接操作 Chroma（经 RAG service）。

### 2. 目标表结构（详细设计 §6）
```
users, courses, documents, knowledge, mindmaps, questions,
question_options, answer_records, wrong_questions, agent_tasks
```

### 3. 实体职责区分（重要）
严格区分「题目本身信息」与「用户对题目的学习/答题记录」：
- **题目本身**：`questions` + `question_options`（content/options/answer/analysis/knowledge_id/difficulty）。
- **学习记录**：`answer_records`（答题）、`wrong_questions`（错题）、`review_cards`（SM-2 复习卡）、`review_logs`（复习日志）。
- 二者通过 `question_id` 关联，不把用户记录塞进题目表。

### 4. 状态机
- `documents.status`: pending / processing / success / failed
- `agent_tasks.status`: pending / running / success / failed / cancelled
- 题目生命周期：GENERATED → REVIEWING → APPROVED（失败 REJECTED → REGENERATING）

### 5. 约束与迁移
- 主键、外键、唯一约束明确（参考现有 8 表：users.email/username 唯一、cards 复合主键）。
- P0 用 `metadata.create_all()` + `db:init` 脚本；Alembic 迁移标记为可后置。
- 现有 Drizzle schema 与 db.ts 存在「重复定义」隐患，新库统一以 SQLAlchemy 模型为唯一真相源。

### 6. Agent 访问
- Agent **禁止直接执行 SQL**，必须走 `Tool → Service → Repository → Database`。

### 参考
- 现有 `server/src/db/schema.ts`、`server/src/db.ts`（表设计蓝本）。
