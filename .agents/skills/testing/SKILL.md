---
name: testing
description: EStudy 测试规范（pytest + 前端 vitest）。当编写/运行单元测试、Agent 结构测试、核心流程测试时加载。
---

# testing — 测试规范

## 用途
指导测试编写，确保确定性逻辑有单测覆盖，Agent 输出有结构校验，核心链路有流程测试。

## 何时加载
- 编写/修改 `backend/tests/*` 或 `frontend/src/**/*.spec.ts`
- 运行测试、验证修改时

## 必须遵守的规范

### 1. 单元测试（确定性逻辑）
优先覆盖：`Parser / Chunker / RAG Retriever / Question Validator / Answer Checker / Permission Checker`。
- 后端用 **pytest**；前端用 **vitest**。

### 2. Agent 测试
- **不比较完整字符串**，只验证输出结构：如 Question Agent 是否产出 N 道题、题型是否正确、每题是否有答案。
- LLM 调用在测试中 mock（不真实调用 API）。

### 3. 核心流程测试（P0 至少三条）
1. 资料导入：PDF → 解析 → 知识点 → 思维导图 → RAG
2. AI 出题：资料 → RAG → Question Agent → Review Agent → 题库
3. 刷题：题库 → 答题 → 判题 → 错题

### 4. 现有基线（迁移前已跑通）
- 前端：`vitest run` — 6 文件 78 用例 ✅
- 后端（Express 旧）：`vitest run`（server）— 1 文件 12 用例 ✅
- 迁移到 FastAPI 后需重建等价测试。

### 5. 修改代码后的验证要求（硬约束）
每次修改后依次：① 类型检查 ② 单元/Agent 测试 ③ 后端启动自检（/api/health）④ 前端构建/启动自检 ⑤ LLM 相关改动确认三层校验与重试上限。验证通过后再汇报，不得在未验证时声称完成。

### 参考
- docs：`详细设计Pt.3.md` §20（测试设计）、§21（MVP 验收）。
