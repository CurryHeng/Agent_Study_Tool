# EStudy AI 系统架构分析（架构评审稿）

> 2026-08-15 · 状态：**已采纳**（已融合进 AGENTS.md §5/§6 与（必读）总体设计文档 §四/§十三，任务分级见本文 §三/§四 与项目进度 §〇.〇）
> 输入材料：项目需求说明书、总体设计、详细设计、26 条实际路由、backend 代码、竞品横向对比报告、FSRS-6 迁移后现状、DeepSeek function calling 原型验证记录。

---

# 第一部分：业务能力拆解

| 能力域  | 核心功能               | 输入                 | 输出（资产）       | 主要技术                       |
| ---- | ------------------ | ------------------ | ------------ | -------------------------- |
| 资料管理 | 上传/解析/存储/状态机/重建索引  | PDF/MD/Word/PPT/图片 | 结构化章节 + 原文文件 | parsers 工厂、文档状态机           |
| 知识加工 | 章节识别→知识点提取→层级构建→导图 | 解析后文本              | 知识树 + 思维导图   | 规则引擎、LLM 抽样交叉验证、markmap    |
| 语义检索 | 切块→嵌入→存储→检索        | 章节文本、查询词           | 相关知识片段       | Chroma + 本地 ONNX embedding |
| 题目生产 | 生成→三层校验→审题→回环≤2→入库 | 知识点+题型+数量+RAG 上下文  | approved 题目  | LLM + 确定性校验器               |
| 题库运营 | CRUD/软删/收藏/搜索/举一反三 | 用户操作               | 题库资产         | 纯业务 SQL                    |
| 学习训练 | 判题→答题记录→FSRS 调度    | 学生作答               | 答题记录 + 复习卡   | 确定性判题 + FSRS-6             |
| 学习分析 | 聚合统计→掌握度→薄弱点→热力图   | 答题记录/复习卡/错题        | 统计报表         | SQL 聚合（/api/stats）         |
| 错因诊断 | 错题归因→改进建议          | 错题+错误作答+解析         | 结构化错因        | LLM 单次调用+结构化校验             |
| 学习干预 | 针对性练习/学习计划         | 诊断结论               | 干预方案         | 组合调用生产域+计划规则               |
| 智能交互 | 开放式输入→理解→编排→应答     | 自然语言+上下文           | 回复+任务结果+步骤流  | **唯一开放式域**                 |

关键观察：前 9 个域输入输出明确、流程预先可知；只有第 10 域下一步不可预知。

---

# 第二部分：Agent / Pipeline / Service 判定

| 模块 | 判定 | 原因 |
|---|---|---|
| 文档解析/存储 | Service | 零不确定性 |
| 知识加工（含导图） | Pipeline | 步骤固定；LLM 提取只是管线内节点；校验回环是规则 |
| 语义检索 | Service | 确定性数学运算 |
| 题目生产 | Pipeline | 提议-审核回环是质量规则，不是决策 |
| 题库运营 | Service | 纯 CRUD |
| 学习训练（判题+FSRS） | Service | 算法必须可复现、可单测 |
| 学习分析 | Service | 聚合统计 |
| 错因诊断 | Service（LLM 增强） | 单次结构化生成，无多步规划 |
| 学习干预 | Pipeline（编排生产域） | 诊断→选题→出题顺序固定 |
| **智能交互/答疑** | **Agent（ReAct）** | 唯一满足四条标准：开放目标、动态规划、路径不定、跨系统组合 |
| AI 导师（未来） | Agent | 开放式多轮辅导，与交互域同构 |

## 学习策略模块专项判定

| 模块 | 判定 | 说明 |
|---|---|---|
| 错题记录 | 确定性 Service | 只增不改，无 LLM |
| 掌握度计算 | 确定性 Service | 聚合公式；语义化描述可 LLM 增强但不改计算本身 |
| FSRS 复习调度 | 确定性 Service | 已完成 SM-2→FSRS-6 迁移，绝不 Agent 化 |
| 学习推荐 | 混合 | 选题逻辑确定性；推荐理由/建议文案 LLM 增强；被教练专家调用 |

---

# 第三部分：候选方案对比

## 方案 A：偏 Agent 化（6+ 领域 Agent 各自带循环）
- 优点：叙事最"多 Agent"；每域自治
- 缺点：固定流程被强行 Agent 化后每步问 LLM"下一步干嘛"——Token 成本 ×3-5、审题闸门可能被跳过、测试无法确定性断言
- 开发成本：高（全部重写+全套新测试）　长期扩展性：差　**适合：否（炫技型架构）**

## 方案 B：Agent + Pipeline 混合（1 主 + 3 专家，supervisor 模式）★推荐
- 优点：决策只发生在开放入口；专家内部流水线（可测、省钱）；对外多 Agent 协作成立（助手调出题专家、教练再调出题专家）；OpenTutor"3 专家代理"先例验证；"多 Agent 编排"护城河叙事成立且诚实
- 缺点：supervisor 需写好工具描述与护栏（max_iterations、权限）；比 C 多一层抽象
- 开发成本：中——90% 现有代码不动，只重构 graph.py + 工具薄封装　长期扩展性：好　**适合：是**

## 方案 C：单 Agent + 多工具
- 优点：最简单、最好测、成本最低
- 缺点：放弃多 Agent 叙事（竞品报告钦定护城河）；工具 >8 个后 prompt 臃肿、选择准确率下降；答辩无亮点
- 开发成本：最低　长期扩展性：中　**适合：工程可行，战略丢分**

---

# 第四部分：推荐架构（方案 B）

## 1. Agent 数量：4 个（1 主 + 3 专家）

全系统只有交互入口存在真决策（ReAct 只配在这里）；三个专家对应三条含"LLM 语义判断"的资产生产线（知识/题目/诊断），内部流水线保证质量与成本。总数与 OpenTutor 专家制同构，与四人分工天然对齐。

## 2. Agent 职责

| 名称                                | 职责                         | 输入                       | 输出                     | 内部能力                                  | 不负责          |
| --------------------------------- | -------------------------- | ------------------------ | ---------------------- | ------------------------------------- | ------------ |
| **助手·导师**（主，原 Navigator+Tutor 合并） | 意图理解、任务编排、答疑、辅导            | 自然语言+对话历史+workbook+页面上下文 | reply + steps[] + 专家结果 | ReAct 循环（max_iter=8）、工具选择、多轮记忆、教学模式切换 | SQL、出题、审题、诊断 |
| **知识专家**（原 Document+Knowledge）    | 文档语义理解→知识点→层级→导图           | 解析后章节文本                  | 知识树+导图数据               | 内部 Pipeline：规则引擎→LLM 抽样交叉验证→校验回环≤2    | 与用户直接对话      |
| **出题专家**（原 Question+Review）       | 按主题/知识点出题并保质入库             | 主题+题型+数量+难度              | approved 题目+审题报告       | 内部 Pipeline：RAG→生成→三层校验→审题→回环≤2→入库    | 诊断、调度        |
| **教练专家**（原 Error+评估，新建）           | 错因归因→薄弱诊断→调出题专家生成补救练习→学习建议 | 用户 ID+时间范围               | 诊断报告+补救题+建议            | 统计聚合（确定性）→LLM 归因→条件分支→跨专家调用           | 调度、对话        |

所有专家不直接操作数据库（走 Service→Repository）。

## 3. Pipeline / Service 红线（必须保持确定性）

| 模块 | 形态 | 绝不 Agent 化的理由 |
|---|---|---|
| 文档解析 | Service | 零不确定性 |
| 判题 | Service | 判分必须可复现 |
| FSRS-6 调度 | Service | 算法正确性靠单测保证 |
| 错题记录 | Service | 只增不改的历史数据 |
| 掌握度/热力图聚合 | Service | 纯 SQL |
| 知识加工 | Pipeline（知识专家内部） | 步骤固定+校验回环是规则 |
| 出题审题 | Pipeline（出题专家内部） | 质量闸门是规则 |

---

# 第五部分：对话 Agent 如何服务全局

## 5.1 总原则：对话 Agent = 产品的自然语言外壳

```
                    ┌─ UI 通道（按钮/页面）→ 确定性服务      （高频、结构化操作）
用户意图 ────────────┤
                    └─ 对话通道（聊天）→ 主 Agent → 工具      （模糊、复合、懒人操作）
```

对话是编排层不是替代品：刷题等高频操作走 UI 更快；"把第三章错题归因再针对薄弱点出 5 道题"这种复合请求，UI 点 7 次，对话一句搞定。

## 5.2 全局意图地图

| 用户可能说的话 | 意图 | 工具 | 级别 |
|---|---|---|---|
| "这份资料讲了什么" | 资料摘要 | search_documents | 读 |
| "整理刚传的资料" | 知识加工 | import_knowledge | 写 |
| "把反向传播那节改简单点" | 知识编辑 | get_knowledge_tree → update_knowledge_node | 写 |
| "这一章展开几个子知识点" | 知识扩充 | add_knowledge_node | 写 |
| "删掉这个知识点" | 知识编辑 | delete_knowledge_node | 写 |
| "出 10 道单选" | 出题 | generate_questions（内含审题回环） | 写 |
| "这道题太难，换一道" | 题目修改 | update_question / regenerate | 写 |
| "收藏/删掉这道题" | 题库管理 | favorite_question / delete_question | 写 |
| "来道类似的" | 举一反三 | similar_question | 读（收藏才写） |
| "我要刷题/开始复习" | 启动训练 | navigate("/review") | 导航 |
| "这道题为什么算我错" | 判题解释 | get_question + 直接解释 | 读 |
| "分析我的错题" | 错因归因 | analyze_wrong_reason | 写 |
| "我哪里薄弱" | 诊断 | get_stats → 教练专家 | 读 |
| "针对薄弱点出题" | 干预 | 教练诊断 → generate_questions（复合链） | 写 |
| "帮我制定学习计划" | 规划 | get_stats + get_due → create_plan | 写 |
| "今天该学什么" | 建议 | get_due + get_stats | 读 |
| "怎么上传资料" | 功能指导 | 直接答 + navigate("/upload") | 导航 |
| "什么是反向传播" | 答疑 | search_documents → RAG 增强回答 | 读 |

## 5.3 三个横切机制

**① 上下文注入**（否则"这里/刚才那道"无法消解）：

```json
{ "message": "把这里改简单点",
  "workbook_id": 4,
  "context": { "view": "mindmap", "selected_knowledge_id": 342 } }
```

Agent system prompt 写明"用户说的'这里/这个'优先看 context"，比从对话历史猜可靠。

**② 导航指令**（Agent 不必在聊天里做完所有事）：`navigate(route)` 工具返回 UI 指令，前端跳转。"我要刷题"→"好，带你去刷题页"+跳转。这是对話与 UI 通道的衔接器。

**③ 写操作统一两阶段确认**：所有写级工具不直接落库：

```
propose（生成操作提案）→ 前端渲染通用确认卡片 → 用户确认 → confirm 执行
```

前端只需做**一个通用确认卡片组件**；后端所有写工具返回统一 proposal 结构。不做 LangGraph interrupt（复杂），做两阶段 API（简单、可测）。

## 5.4 写操作示例："把反向传播那节改简单点"

```
用户输入 → 主 Agent
  [工具] get_knowledge_tree()        → 定位"反向传播"=节点342
  [工具] get_knowledge_detail(342)   → 读出现有内容
  LLM 生成简化文案
  [决策] 生成提案："将『反向传播算法通过链式法则…』简化为『反向传播就是
         从后往前一步步算该怎么调整』"
  ⏸ 返回提案卡片，等用户确认          ← 指代消解错了也能在此拦下
  用户确认 → update_knowledge_node(342, ...)
  回复："已修改，思维导图页可查看"
```

---

# 第六部分：RAG 与 Embedding 的角色

## 一句话

- **Embedding**：把文字变成向量（语义坐标），语义越近距离越近
- **RAG**：**先查资料，再回答**——回答前先从用户资料库捞出最相关的几段，基于这几段说话

## 为什么必须有

LLM 两个致命局限：①没读过用户的教材；②整本教材塞不进 prompt（超 token 且贵）。

```
上传时（建库）：教材 → 切块 → embedding → Chroma 向量库
使用时（检索）：查询词 → embedding → 取最相关 3-5 段 → 随指令发给 LLM
                → 输出严格基于用户的资料
```

## 在 EStudy 的三个用途

| 用途 | 没有它会怎样 |
|---|---|
| 出题有据可依 | LLM 瞎编通用题（原型验证过：无资料时出"什么是ReAct"，有资料才出"链式法则"） |
| 答疑贴合课程 | 回答用通用解释而非老师课件的讲法 |
| 错因分析有上下文 | 看不到题目出自哪段资料，建议空泛 |

成本为零：embedding 用本地 ONNX MiniLM，不调 API、离线可用。

## 架构位置

```
资料 Service → 知识专家（提取）→ 知识树
                    ↓
              RAG Service（embedding + Chroma）  ← 公共基础设施，不是 Agent
                    ↓ 被工具消费
   search_documents / generate_questions / analyze_wrong_reason
```

---

# 第七部分：运行流程（典型场景）

**场景 1：上传教材生成知识体系**
```
上传 PDF → 资料 Service（存储+解析）→ 自动触发知识专家 Pipeline（不经主 Agent）
→ 章节→知识点→导图→自动索引 → 知识树+导图入库
```

**场景 2：生成练习题**
```
"出 10 道反向传播单选" → 主 Agent：search_documents → 观察
→ 调出题专家(topic,count) → 内部生成→审题回环 → steps[]+题目列表
```

**场景 3：问薄弱点**
```
"我哪里薄弱？" → 主 Agent → get_stats → 教练专家（读错题+记录→LLM 归因）
→ 诊断+建议 → 可选：自动调出题专家出补救题
```

**场景 4：制定学习计划**
```
"帮我制定计划" → 主 Agent（导师模式）→ get_stats + FSRS due 分布
→ create_plan 提案 → 用户确认 → 计划入库
```

**场景 5：对话改导图**
```
"把第三章改简单点" → get_knowledge_tree 定位 → 生成简化提案
→ 确认卡片 → update_knowledge_node → 导图页可查
```

---

# 第八部分：现有代码迁移清单

| 处理 | 模块 |
|---|---|
| **直接保留** | import_graph（=知识专家主体）、generation/review/question_validator（=出题专家主体）、rag/grading/fsrs_scheduler/stats/wrong_record、全部 repository、全部前端页面 |
| **包装成 Tool**（≤30 行薄封装，参数带语义引导） | rag.retrieve、generate_questions、mindmap、stats、错因分析、import 入口、知识节点增删改（梓恒 C2 接口复用）、favorite/delete question |
| **重构** | `workflow/graph.py`（固定 INTENT_PLAN 图 → create_react_agent supervisor + 3 专家子图）、`agent_service.run_task`（包 ReAct 循环 + AgentTask 日志 + steps 上报） |
| **新增** | `workflow/tools.py`（工具层+读写分级）、`services/coach_service.py`（教练专家）、主 Agent system prompt（含教学模式）、两阶段 proposal 机制、navigate 指令、聊天请求 context 字段、前端通用确认卡片组件、AgentChatView |
| **删除** | Orchestrator 独立节点、INTENT_PLAN 映射 |

## 工具清单终版

| 级别 | 工具 |
|---|---|
| 读（直接执行） | search_documents、get_knowledge_tree、get_knowledge_detail、get_question、list_questions、get_stats、get_due、similar_question |
| 导航（前端执行） | navigate(route) |
| 写（两阶段确认） | generate_questions、import_knowledge、update_knowledge_node、add_knowledge_node、delete_knowledge_node、update_question、delete_question、favorite_question、analyze_wrong_reason、create_plan |

---

# 第九部分：测试迁移策略

- Pipeline 内部测试（出题/审题/导入/FSRS）**全部不动**（164 个测试保持绿）
- 图流程测试（test_agent.py 13 个）改为 Mock tool_calls：断言"正确任务调用了正确工具、正确顺序"
- 新增：写操作两阶段流程测试（propose 不落库 → confirm 才落库）、上下文注入测试（"这里"→ 正确节点）、max_iterations 熔断测试

---

# 第十部分：与四人分工的映射

| 成员 | 本架构下的任务 |
|---|---|
| 王悦（D） | supervisor 主 Agent + 工具层 + steps 上报 + 两阶段 proposal 后端 |
| 蔡（B） | 出题专家调优 + 教练专家（错因分析+诊断+补救题链） + LLM 填空判分 |
| 梓恒（C） | 导图显示优化 + 知识节点编辑接口（同时服务 UI 右键和 Agent 工具） + LLM 分支生成 |
| 你（A） | AgentChatView（含通用确认卡片+steps 展示+navigate 跳转）+ 出题 UI + 统计热力图 + 图片导入 + 前端测试 |

---

# 评审备查

- ReAct 原型验证：DeepSeek function calling 可用，复合任务"检索→出题"自主完成，含并行工具调用（2026-08-15，react_prototype.py）
- 关键教训：工具参数必须带语义引导（topic），否则 LLM 只能按练习册名瞎编
- 架构原则延续 AGENTS.md §4：确定性逻辑不进 Agent；Agent 不碰 SQL；结构化传递；LLM 输出必经校验
