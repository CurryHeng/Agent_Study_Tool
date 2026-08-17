# Issue #40：写操作两阶段确认接口契约

> 对接范围：后端 #40 与前端确认卡片 #45  
> 状态：已实现并通过真实联调  
> API 前缀：`/api/agent`

## 1. 流程说明

所有 Agent 写操作都遵循两阶段流程：

```text
用户提出写操作
  → POST /api/agent/chat
  → 后端生成 proposal，数据库不发生业务写入
  → 前端展示确认卡片
  → 用户确认或取消
  → POST /api/agent/confirm
  → approved=true 时执行，approved=false 时丢弃
```

proposal 具有以下约束：

- 有效期为 600 秒；
- 绑定创建它的登录用户；
- 只能消费一次；
- 确认执行时会再次进行权限校验；
- 取消、过期或越权均不会修改业务数据。

## 2. 聊天接口

### 请求

```http
POST /api/agent/chat
Authorization: Bearer <access_token>
Content-Type: application/json
```

```json
{
  "message": "删除知识点 ID 16",
  "workbook_id": 1
}
```

### 响应

```json
{
  "task_id": "task-uuid",
  "conversation_id": null,
  "reply": "已生成删除提案，请在确认卡片中处理。",
  "steps": [
    {
      "tool": "delete_knowledge_node",
      "args": {
        "knowledge_id": 16
      },
      "ok": true,
      "summary": "删除知识点“知识点名称”"
    }
  ],
  "proposals": [
    {
      "proposal_id": "00da0767-00d8-4fa3-86d0-37c2fc82c037",
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
  ],
  "navigate": null,
  "intent": "delete_knowledge_node",
  "result": {
    "reply": "已生成删除提案，请在确认卡片中处理。",
    "last_tool": "delete_knowledge_node"
  }
}
```

## 3. Proposal 统一结构

```ts
interface AgentProposal {
  proposal_id: string
  action: string
  target: Record<string, unknown>
  changes: Record<string, unknown>
  impact: string
  expires_in_sec: number
}
```

字段说明：

| 字段 | 类型 | 说明 |
|---|---|---|
| `proposal_id` | `string` | 提案 UUID，确认接口的唯一凭据 |
| `action` | `string` | 写工具动作名，用于前端显示操作类型 |
| `target` | `object` | 操作目标，例如知识点 ID、名称或练习册 ID |
| `changes` | `object` | 统一包含 `before` 和 `after`，用于展示变更对比 |
| `impact` | `string` | 面向用户的影响说明 |
| `expires_in_sec` | `number` | 剩余有效期，当前固定为 600 秒 |

当前支持的 `action`：

| action | 用途 |
|---|---|
| `generate_questions` | 生成并审核题目，确认后写入题库 |
| `add_knowledge_node` | 新增知识点 |
| `update_knowledge_node` | 修改知识点 |
| `delete_knowledge_node` | 删除知识点 |

## 4. 确认或取消接口

### 请求

```http
POST /api/agent/confirm
Authorization: Bearer <access_token>
Content-Type: application/json
```

确认执行：

```json
{
  "proposal_id": "00da0767-00d8-4fa3-86d0-37c2fc82c037",
  "approved": true
}
```

取消提案：

```json
{
  "proposal_id": "00da0767-00d8-4fa3-86d0-37c2fc82c037",
  "approved": false
}
```

## 5. 响应示例

### 确认删除知识点

```json
{
  "ok": true,
  "result": {
    "deleted": true,
    "knowledge_id": 16
  }
}
```

### 取消提案

```json
{
  "ok": true,
  "result": {
    "approved": false
  }
}
```

### 确认生成题目

```json
{
  "ok": true,
  "result": {
    "saved": 5,
    "questions": []
  }
}
```

其他动作的 `result` 为相应 Service 的结构化执行结果，前端不应依赖不同动作具有完全相同的 `result` 字段。

## 6. 错误状态

| HTTP 状态码 | 场景 | 数据是否修改 |
|---|---|---|
| `401` | 未登录或令牌失效 | 否 |
| `404` | 提案不存在、属于其他用户或已被消费 | 否 |
| `410` | 提案超过 600 秒有效期 | 否 |
| `422` | 请求结构错误或动作不受支持 | 否 |

为了避免泄露其他用户的提案是否存在，跨用户确认统一返回 `404`。

## 7. 前端对接要求

1. 收到 `proposals[]` 后，根据 `action`、`target`、`changes` 和 `impact` 渲染通用确认卡片。
2. 不要让用户通过发送“确认”文本来执行写操作；必须调用 `/api/agent/confirm`。
3. 点击确认时传 `approved: true`，点击取消时传 `approved: false`。
4. 请求成功后禁用该卡片，防止重复提交。
5. `404` 应提示“提案不存在或已处理”；`410` 应提示“提案已过期，请重新发起”。
6. `result` 按动作分别处理，卡片的通用状态只依赖顶层 `ok`。

## 8. 已验证行为

- 删除提案生成后，数据库中的目标知识点仍然存在；
- 点击“确认执行”后，目标知识点才从数据库删除；
- 取消提案不会修改数据；
- 过期提案不会修改数据；
- 其他用户无法确认该提案；
- 同一提案重复确认会返回 `404`；
- 前端确认卡片已能正常展示并调用确认接口。
