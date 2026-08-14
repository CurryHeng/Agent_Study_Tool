---
name: backend
description: StudyForge 后端（FastAPI）开发规范。当编写或修改 backend/ 下的 FastAPI 路由、Service、Repository、config、认证中间件时加载。
---

# backend — FastAPI 后端开发规范

## 用途
指导 FastAPI 后端的开发，确保严格遵守 docs 确定的分层架构与工程约束。

## 何时加载
- 编写/修改 `backend/api/*`、`backend/services/*`、`backend/repositories/*`、`backend/models/*`、`backend/config.py`
- 涉及认证、文件上传、题库、刷题等后端接口时

## 必须遵守的规范

### 1. 分层架构（硬约束）
```
API (路由) → Service (业务) → Repository (数据访问) → Database
```
- **禁止**路由层直接写 SQL / 直接调用 Repository 之外的数据库操作。
- **禁止**下层依赖上层（Repository 不得 import API 路由）。
- Agent 相关的调用走：`API → Agent Service → Navigator → Orchestrator → 专业 Agent → Tools/RAG/LLM → Service → Repository`。

### 2. 配置与密钥
- 所有密钥/模型参数/路径一律读 `.env`，由 `config.py` 统一读取（`pydantic-settings`）。
- 禁止硬编码 API Key、JWT_SECRET、ENCRYPTION_KEY。
- 生产环境校验：JWT_SECRET 不得使用默认值（参考现有 `server/src/lib/jwt.ts` 的 FATAL 检查）。

### 3. 确定性逻辑 vs Agent
- 登录、文件上传/存储、PDF 读取、判题、权限校验等确定性逻辑用**普通函数/服务**，禁止调用 LLM。
- 只有内容理解、知识提取、出题、审核、任务规划等非确定性任务才交给 Agent。

### 4. 校验
- 请求体用 Pydantic v2 schema 校验；LLM 输出入库前必须过「格式→结构→业务」三层校验（详见 langgraph skill）。

### 5. 错误与日志
- 统一错误响应格式 `{ "error": "..." }`。
- Agent 任务记录 `task_id / user_id / agent_name / node_name / start_time / end_time / status / error`，不静默吞错。

### 6. 编码规范
- 遵循 PEP 8；使用 `ruff` 做 lint + format；类型标注完善（目标 mypy 可过）。
- 复用现有 Express 代码逻辑（JWT refresh 轮换、AES-256-GCM 加密、SM-2）时保持行为一致，但按 FastAPI 习惯重写。

### 参考代码
- 现有 Express 后端：`server/src/routes/auth.ts`、`server/src/lib/jwt.ts`、`server/src/lib/crypto.ts`、`server/src/lib/sm2.ts`（仅作逻辑参考）。
