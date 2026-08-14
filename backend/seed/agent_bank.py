"""内置 Agent 题库数据：《深入理解 AI Agent》第 1-2 章（学习概要 v1.4）。

来源：E:\\agent学习\\AI-Agent学习概要-第1-2章.md
结构：KNOWLEDGE_TREE = (章节, [知识点...])；QUESTIONS 按章节/知识点挂载。
题型覆盖 single_choice / multiple_choice / true_false / fill_blank / short_answer。
"""

# (章节名, [知识点名, ...])——章节为一级节点，知识点为二级节点
KNOWLEDGE_TREE: list[tuple[str, list[str]]] = [
    (
        "第1章 AI Agent 概述",
        [
            "1.1 核心公式：Agent = LLM + 上下文 + 工具",
            "1.2 “模型即 Agent”新范式",
            "1.3 ReAct 循环",
            "1.4 Harness 工程",
        ],
    ),
    (
        "第2章 上下文工程",
        [
            "2.1 核心命题：上下文决定上限",
            "2.2 完整上下文的组成",
            "2.3 四大消息角色",
            "2.4 上下文分层架构",
            "2.5 KV Cache 管理",
            "2.6 系统提示词与提示工程",
            "2.7 Agent Skills 渐进式披露",
            "2.8 上下文压缩策略",
            "2.9 Prompt 注入",
        ],
    ),
]

# type: single_choice / multiple_choice / true_false / fill_blank / short_answer
# options 仅选择题需要；answer：选择填字母（多选字母相连）、判断填 true/false、其余填文本
QUESTIONS: list[dict] = [
    # ── 第 1 章 ──
    {
        "chapter": "第1章 AI Agent 概述",
        "knowledge": "1.1 核心公式：Agent = LLM + 上下文 + 工具",
        "type": "single_choice",
        "content": "在 Agent 核心公式中，LLM 被比喻为什么？",
        "options": [("A", "大脑"), ("B", "眼睛"), ("C", "双手"), ("D", "缰绳")],
        "answer": "A",
        "analysis": "Agent = LLM（大脑）+ 上下文（眼睛）+ 工具（双手）。LLM 负责理解、推理、决策。",
        "difficulty": 1,
    },
    {
        "chapter": "第1章 AI Agent 概述",
        "knowledge": "1.1 核心公式：Agent = LLM + 上下文 + 工具",
        "type": "multiple_choice",
        "content": "Agent 的核心公式包含哪些组件？",
        "options": [("A", "LLM"), ("B", "上下文"), ("C", "工具"), ("D", "强化学习环境")],
        "answer": "ABC",
        "analysis": "Agent = LLM（大脑）+ 上下文（眼睛）+ 工具（双手），不含强化学习环境。",
        "difficulty": 1,
    },
    {
        "chapter": "第1章 AI Agent 概述",
        "knowledge": "1.1 核心公式：Agent = LLM + 上下文 + 工具",
        "type": "fill_blank",
        "content": "在 Agent 核心公式中，上下文被比喻为 Agent 的____。",
        "answer": "眼睛",
        "analysis": "上下文 = 系统指令、对话历史、推理过程、工具记录等一切模型可读取的信息，"
        "比喻为眼睛/操作系统。",
        "difficulty": 1,
    },
    {
        "chapter": "第1章 AI Agent 概述",
        "knowledge": "1.2 “模型即 Agent”新范式",
        "type": "single_choice",
        "content": "与传统强化学习 Agent 相比，LLM Agent 的样本效率大约可提升多少倍？",
        "options": [("A", "2-4 倍"), ("B", "10-20 倍"), ("C", "250-400 倍"), ("D", "10000 倍以上")],
        "answer": "C",
        "analysis": "LLM Agent 携带海量先验知识，样本效率可提升 "
        "250-400 倍；先验知识的重要性超越算法和环境本身。",
        "difficulty": 2,
    },
    {
        "chapter": "第1章 AI Agent 概述",
        "knowledge": "1.3 ReAct 循环",
        "type": "single_choice",
        "content": "在 ReAct 循环（思考→行动→观察）中，框架与模型的职责分别是？",
        "options": [
            ("A", "框架负责决策，模型负责执行工具"),
            ("B", "框架负责执行工具，模型只负责决策"),
            ("C", "框架和模型共同执行工具"),
            ("D", "模型既决策又直接操作文件系统"),
        ],
        "answer": "B",
        "analysis": "关键原则：框架负责执行工具，模型只负责决策（输出 tool_calls 或最终答案）。",
        "difficulty": 1,
    },
    {
        "chapter": "第1章 AI Agent 概述",
        "knowledge": "1.3 ReAct 循环",
        "type": "true_false",
        "content": "ReAct 循环必须设置最大迭代次数，以防止模型陷入死循环。",
        "answer": "true",
        "analysis": "关键原则之一：必须设置最大迭代次数防止死循环；"
        "消息持续追加，完整保留交互轨迹。",
        "difficulty": 1,
    },
    {
        "chapter": "第1章 AI Agent 概述",
        "knowledge": "1.4 Harness 工程",
        "type": "fill_blank",
        "content": "“Harness”本意是____，比喻模型之外控制与赋能 Agent 的一切工程能力。",
        "answer": "马具",
        "analysis": "控制马靠的不是马的力量，而是骑手的缰绳。"
        "模型是马，Harness 是缰绳、马鞍、马镫。",
        "difficulty": 1,
    },
    {
        "chapter": "第1章 AI Agent 概述",
        "knowledge": "1.4 Harness 工程",
        "type": "multiple_choice",
        "content": "Harness 工程包含哪些组成部分？",
        "options": [
            ("A", "上下文管理"),
            ("B", "工具设计"),
            ("C", "记忆组织与异常恢复"),
            ("D", "模型预训练"),
        ],
        "answer": "ABC",
        "analysis": "Harness = 上下文管理、工具设计、记忆组织、"
        "异常恢复等模型之外的工程基础设施，不含预训练。",
        "difficulty": 2,
    },
    {
        "chapter": "第1章 AI Agent 概述",
        "knowledge": "1.4 Harness 工程",
        "type": "short_answer",
        "content": "简述 Harness 工程中“模型”与“Harness”的关系，"
        "并说明为什么它被称为本章的灵魂概念。",
        "answer": (
            "模型是马（提供动力），Harness 是缰绳、马鞍、马镫（上下文管理、工具设计、记忆组织、"
            "异常恢复）。决定 Agent 上限的往往不是底层模型多强，而是这些模型之外的工程基础设施，"
            "因此说“模型之外的一切工程能力，才是真正的竞争力所在”。"
        ),
        "analysis": "围绕“模型提供动力、Harness 决定上限”作答即可。",
        "difficulty": 3,
    },
    # ── 第 2 章 ──
    {
        "chapter": "第2章 上下文工程",
        "knowledge": "2.1 核心命题：上下文决定上限",
        "type": "true_false",
        "content": "第 2 章的核心命题是：模型参数规模决定 Agent 能力的上限。",
        "answer": "false",
        "analysis": "核心命题是“上下文决定 Agent 能力的上限”："
        "中等模型 + 精心组织的上下文常优于顶级模型 "
        "+ 信息缺失。",
        "difficulty": 1,
    },
    {
        "chapter": "第2章 上下文工程",
        "knowledge": "2.2 完整上下文的组成",
        "type": "single_choice",
        "content": "下列哪一项不属于“完整上下文”的组成部分？",
        "options": [
            ("A", "系统指令"),
            ("B", "对话历史"),
            ("C", "模型权重"),
            ("D", "外部知识"),
        ],
        "answer": "C",
        "analysis": "完整上下文 = 系统指令 + 对话历史 + 推理过程 "
        "+ 工具记录 + 用户记忆 + 外部知识；模型权重不在其中。",
        "difficulty": 1,
    },
    {
        "chapter": "第2章 上下文工程",
        "knowledge": "2.3 四大消息角色",
        "type": "single_choice",
        "content": "四大消息角色中，固定置于消息头部、优先级最高的是？",
        "options": [("A", "system"), ("B", "user"), ("C", "assistant"), ("D", "tool")],
        "answer": "A",
        "analysis": "system 定义 Agent 身份、约束、全局规则，固定置于消息头部，优先级最高。",
        "difficulty": 1,
    },
    {
        "chapter": "第2章 上下文工程",
        "knowledge": "2.3 四大消息角色",
        "type": "fill_blank",
        "content": "工具执行结果以____角色消息追加，并通过 tool_call_id 与调用绑定。",
        "answer": "tool",
        "analysis": "四大角色：system / user / assistant / tool；tool 消息携带工具执行结果。",
        "difficulty": 1,
    },
    {
        "chapter": "第2章 上下文工程",
        "knowledge": "2.5 KV Cache 管理",
        "type": "single_choice",
        "content": "KV Cache 作用的层级是？",
        "options": [
            ("A", "模型推理内部，单次请求内复用计算结果"),
            ("B", "API 服务层，跨多次请求复用前缀"),
            ("C", "数据库层，缓存查询结果"),
            ("D", "客户端层，缓存用户输入"),
        ],
        "answer": "A",
        "analysis": "KV Cache 在模型推理内部、单次请求内复用；"
        "跨请求复用前缀的是 Prompt Cache（API 服务层）。",
        "difficulty": 2,
    },
    {
        "chapter": "第2章 上下文工程",
        "knowledge": "2.5 KV Cache 管理",
        "type": "multiple_choice",
        "content": "KV Cache 管理的三大落地准则包括哪些？",
        "options": [
            ("A", "系统提示词与工具定义定稿后尽量固定"),
            ("B", "动态信息追加到对话末尾，不嵌入系统提示词"),
            ("C", "优先使用标准 API 结构化消息"),
            ("D", "手动拼接 USER:/ASSISTANT: 纯文本格式"),
        ],
        "answer": "ABC",
        "analysis": "D 是常见错误做法：手动拼接会破坏模型对角色和工具调用的理解。",
        "difficulty": 2,
    },
    {
        "chapter": "第2章 上下文工程",
        "knowledge": "2.5 KV Cache 管理",
        "type": "true_false",
        "content": "把时间戳写入 system 提示词，会导致 KV Cache 每次请求前缀不同而永久失效。",
        "answer": "true",
        "analysis": "前缀任意一处改动整套缓存全部失效；动态信息应追加到对话末尾。",
        "difficulty": 1,
    },
    {
        "chapter": "第2章 上下文工程",
        "knowledge": "2.5 KV Cache 管理",
        "type": "true_false",
        "content": "滑动窗口截断历史消息可以保持 KV Cache 前缀稳定。",
        "answer": "false",
        "analysis": "滑动窗口丢弃最早消息，前缀持续变化，是常见错误做法之一。",
        "difficulty": 2,
    },
    {
        "chapter": "第2章 上下文工程",
        "knowledge": "2.6 系统提示词与提示工程",
        "type": "single_choice",
        "content": "根据注意力机制特性，关键信息应放在上下文的什么位置？",
        "options": [
            ("A", "正中间"),
            ("B", "开头和结尾"),
            ("C", "任意位置效果相同"),
            ("D", "只放在结尾"),
        ],
        "answer": "B",
        "analysis": "模型更容易记住首尾内容；且序列首个 token "
        "承接大量冗余注意力权重（注意力储存池效应）。",
        "difficulty": 1,
    },
    {
        "chapter": "第2章 上下文工程",
        "knowledge": "2.7 Agent Skills 渐进式披露",
        "type": "fill_blank",
        "content": "Agent Skills 采用____式披露：启动时只加载薄目录，按需展开完整 Skill 定义。",
        "answer": "渐进",
        "analysis": "渐进式披露解决上下文窗口有限与信息密度需求之间的矛盾，"
        "类似“需要时才翻详细说明书”。",
        "difficulty": 1,
    },
    {
        "chapter": "第2章 上下文工程",
        "knowledge": "2.8 上下文压缩策略",
        "type": "single_choice",
        "content": "六种上下文压缩策略中，被认为最优的是？",
        "options": [
            ("A", "无压缩，完整保留原始输出"),
            ("B", "个体摘要：每个工具结果独立摘要"),
            ("C", "上下文感知压缩：结合查询意图定向摘要"),
            ("D", "组合摘要：全部结果合并统一摘要"),
        ],
        "answer": "C",
        "analysis": "上下文感知压缩结合查询意图与已有上下文定向摘要，压缩率高且能过滤无关内容。",
        "difficulty": 2,
    },
    {
        "chapter": "第2章 上下文工程",
        "knowledge": "2.8 上下文压缩策略",
        "type": "multiple_choice",
        "content": "生产级分层压缩机制（参考 Claude Code）包括下列哪些？",
        "options": [
            ("A", "工具结果预算控制：大体积输出落磁盘，上下文只放摘要"),
            ("B", "噪声直接删除，无价值内容不生成摘要"),
            ("C", "归档式摘要：逐轮结构化归档，维持对话脉络"),
            ("D", "每轮随机丢弃一半历史消息"),
        ],
        "answer": "ABC",
        "analysis": "此外还有 API 层微压缩与全量 LLM 压缩兜底；随机丢弃历史会破坏上下文连续性。",
        "difficulty": 3,
    },
    {
        "chapter": "第2章 上下文工程",
        "knowledge": "2.8 上下文压缩策略",
        "type": "short_answer",
        "content": "简述上下文压缩的两大动机。",
        "answer": (
            "① 硬件与成本约束：上下文窗口容量有限，token 越多 API 开销越高；"
            "② 上下文腐化（Context Rot）：大量杂乱信息分散模型注意力，装得下但找不到。"
        ),
        "analysis": "答出“窗口/成本约束”和“上下文腐化”两个要点即可。",
        "difficulty": 2,
    },
]
