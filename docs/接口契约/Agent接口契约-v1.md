# Agent 接口契约 v1（简洁版）

> 适用范围：#40 / #41 / #45 / #46 / #47
> 状态：待 D 确认

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

---

## 2. Steps

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
- 非流式，后端返回最终有序数组即可

---

## 3. Proposal

```json
{
  "proposal_id": "uuid",
  "action": "update_knowledge_node",
  "target": {
    "type": "knowledge_node",
    "id": 342
  },
  "payload": {},
  "preview": {
    "before": "原文…",
    "after": "简化后…"
  },
  "impact": "修改 1 个知识点描述",
  "expire_at": "2026-08-16T12:00:00Z",
  "expires_in_sec": 600
}
```

- `payload` 是后端执行时用的数据；前端不依赖它回传
- 后端按 `proposal_id` 缓存，`confirm` 时根据 id 取数据
- `preview` 固定为 `{ before, after }`，用于前端展示
- 默认过期 10 分钟

---

## 4. Confirm

### `POST /api/agent/confirm`

请求：

```json
{
  "proposal_id": "uuid",
  "decision": "approve | reject"
}
```

响应：

```json
{
  "task_id": "uuid",
  "status": "completed | failed",
  "result": {},
  "error": null
}
```

规则：
- `approve` 才落库
- `reject` 静默丢弃
- 重复 confirm：幂等处理
- 过期/不存在：返回 404/410 + `error`

---

## 5. Conversation

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

## 6. 工具分类

| 类型 | 工具 |
|---|---|
| QUERY | `search_documents`、`get_knowledge_tree`、`get_knowledge_detail`、`list_documents`、`get_questions`、`similar_question`、`get_stats`、`get_due` |
| NAVIGATION | `navigate(route)` |
| MUTATION | `add/update/delete_knowledge_node`、`add/update/delete_question`、`favorite_question`、`import_knowledge`、`analyze_wrong_reason`、`create/update_plan`、`generate_questions`（最终版） |

- MUTATION 工具返回 `proposals`
- `generate_questions` 当前为预览版，可暂不算 MUTATION

---

## 7. 兼容策略

- 旧字段 `intent` / `result` 保留，标记 `deprecated`
- 待 #45 联调完成并验证后删除
- 前端新代码不依赖旧字段

---

## 8. 关键决策

1. `conversation_id` 由后端首次返回创建，前端不预创建
2. Proposal 由后端按 id 缓存，前端不负责回传 payload
3. Context 用 `route + entity{type,id}`，`entity` 可为 null
4. v1 不支持流式；steps 为最终数组
5. 错误统一 `{ code, message }`
