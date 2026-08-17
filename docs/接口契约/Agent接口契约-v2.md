# Agent 接口契约 v2（统一版）

> 适用范围：#40 / #41 / #45 / #46 / #47
> 基线：合并 `Agent接口契约-v1.md` 与 D 的 `Issue-40-两阶段确认接口契约.md`
> 状态：待相关人员确认后冻结

---

## 1. Chat

### `POST /api/agent/chat`

请求：

```json
{
  "message": "用户输入",
  "workbook_id": 4,
  "conversation_id": null,
  "context": {
    "route": "/mindmap",
    "entity": {
      "type": "knowledge_node",
      "id": 342
    }
  }
}
```

- `workbook_id` 可选；不传由后端决定默认练习册
- `conversation_id` 不传/为 null = 新会话，由后端创建并返回
- `entity` 允许 null；`type` 枚举：`knowledge_node / question / document / workbook / plan`

响应：

```json
{
  "task_id": "uuid",
  "status": "completed | waiting_confirm | failed | need_input",
  "conversation_id": 12,
  "reply": "文本回复",
  "steps": [],
  "proposals": [],
  "navigate": null,
  "error": null
}
```

- 有 `proposals` 时 `status` 必须为 `waiting_confirm`
- `navigate` 为路由字符串，前端 `router.push`
- `error` 统一 `{ "code": "xxx", "message": "..." }`，无错误为 null
- 保留旧字段 `intent` / `result`，标记 deprecated，迁移完成后删除

---

## 2. Context

```json
{
  "route": "/mindmap",
  "entity": {
    "type": "knowledge_node",
    "id": 342
  }
}
```

- `entity` 可为 null
- `type` 枚举：`knowledge_node / question / document / workbook / plan`
- 用途：支持“修改这里”“分析这个”等上下文指令
- 预留 `extra` 字段供未来扩展

---

## 3. Steps

```json
{
  "id": 1,
  "tool": "get_knowledge_tree",
  "status": "success | failed",
  "args": {},
  "summary": "读取知识树 15 个节点",
  "error": null
}
```

- `args` 后端截断/脱敏，前端主要展示 `summary`
- 工具失败时 `status=failed` 且 `error` 给原因
- 非流式，后端返回最终有序数组即可

---

## 4. Proposal（已按 #40 确认）

```json
{
  "proposal_id": "uuid",
  "action": "delete_knowledge_node",
  "target": {
    "knowledge_id": 16,
    "name": "知识点名称"
  },
  "changes": {
    "before": {
      "name": "知识点名称",
      "description": "原描述"
    },
    "after": null
  },
  "impact": "删除知识点“知识点名称”",
  "expires_in_sec": 600
}
```

字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `proposal_id` | string | 提案 UUID，确认接口唯一凭据 |
| `action` | string | 写工具动作名 |
| `target` | object | 操作目标（知识点/题目/练习册等） |
| `changes` | object | 固定包含 `before` / `after`，用于变更对比 |
| `impact` | string | 面向用户的影响说明 |
| `expires_in_sec` | number | 剩余有效期，默认 600 |

当前支持的 `action`：

- `generate_questions`
- `add_knowledge_node`
- `update_knowledge_node`
- `delete_knowledge_node`

约束：
- proposal 绑定创建用户
- 只能消费一次
- 确认执行时再次做权限校验
- 取消/过期/越权均不修改业务数据

---

## 5. Confirm（已按 #40 确认）

### `POST /api/agent/confirm`

请求：

```json
{
  "proposal_id": "uuid",
  "approved": true
}
```

响应：

```json
{
  "ok": true,
  "result": {
    "deleted": true,
    "knowledge_id": 16
  }
}
```

规则：
- `approved=true` 才落库
- `approved=false` 丢弃，不修改数据
- 重复 confirm 返回 404（提案已消费）
- 过期返回 410
- 跨用户确认统一返回 404

错误状态：

| HTTP | 场景 | 数据是否修改 |
|---|---|---|
| 401 | 未登录/令牌失效 | 否 |
| 404 | 提案不存在/属于他人/已消费 | 否 |
| 410 | 提案过期 | 否 |
| 422 | 请求结构错误或动作不支持 | 否 |

---

## 6. Conversation

接口：

```text
POST   /api/conversations
GET    /api/conversations
GET    /api/conversations/{id}/messages
DELETE /api/conversations/{id}
```

- `POST /api/conversations` 可带 `title`（可选）
- 列表返回：`id / title / created_at / updated_at / last_message`
- 消息接口支持 `limit / offset`
- 消息结构：

```json
{
  "id": 1,
  "conversation_id": 12,
  "role": "user | assistant",
  "content": "你好",
  "metadata": null,
  "created_at": "2026-08-16T12:00:00Z"
}
```

- `metadata` 预留：存 steps / proposals / navigate，便于历史恢复
- 会话按用户隔离

---

## 7. 工具分类

| 类型 | 工具 |
|---|---|
| QUERY | `search_documents`、`get_knowledge_tree`、`get_knowledge_detail`、`list_documents`、`get_questions`、`similar_question`、`get_stats`、`get_due` |
| NAVIGATION | `navigate(route)` |
| MUTATION | `add/update/delete_knowledge_node`、`add/update/delete_question`、`favorite_question`、`import_knowledge`、`analyze_wrong_reason`、`create/update_plan`、`generate_questions`（最终版） |

- MUTATION 工具返回 `proposals`
- `generate_questions` 当前为预览版，可暂不算 MUTATION

---

## 8. 前端对接要求

1. 收到 `proposals[]` 后，根据 `action` / `target` / `changes` / `impact` 渲染通用确认卡片
2. 不要让用户通过发送“确认”文本执行写操作，必须调用 `/api/agent/confirm`
3. 确认传 `approved: true`，取消传 `approved: false`
4. 请求成功后禁用卡片，防止重复提交
5. `404` 提示“提案不存在或已处理”；`410` 提示“提案已过期，请重新发起”
6. `result` 按动作分别处理，卡片通用状态只依赖顶层 `ok`
7. 无 proposal 时不显示确认卡片，不调用 confirm

---

## 9. 关键决策

1. `conversation_id` 由后端首次返回创建，前端不预创建
2. Proposal 由后端按 id 缓存，前端不负责回传 payload
3. Context 用 `route + entity{type,id}`，`entity` 可为 null
4. v1/v2 暂不支持流式；steps 为最终数组
5. 错误统一 `{ code, message }`
6. 旧字段 `intent` / `result` 保留到 #45 联调完成后再删除
