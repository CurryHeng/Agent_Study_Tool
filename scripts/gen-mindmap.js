import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function mdToTree(md) {
  const lines = md.split('\n');
  const root = { content: '', children: [] };
  const stack = [{ level: 0, node: root }];

  for (const line of lines) {
    if (!line.trim()) continue;

    const h1Match = line.match(/^# (.+)/);
    if (h1Match) {
      root.content = h1Match[1];
      continue;
    }

    const h2Match = line.match(/^## (.+)/);
    if (h2Match) {
      while (stack.length > 1) stack.pop();
      const node = { content: h2Match[1], children: [] };
      root.children.push(node);
      stack.push({ level: 1, node });
      continue;
    }

    const liMatch = line.match(/^- (.+)/);
    if (liMatch) {
      while (stack.length > 2) stack.pop();
      const parent = stack[stack.length - 1].node;
      const node = { content: liMatch[1], children: [] };
      parent.children.push(node);
      stack.push({ level: 2, node });
      continue;
    }

    const nestedMatch = line.match(/^  - (.+)/);
    if (nestedMatch) {
      while (stack.length > 3) stack.pop();
      const parent = stack[stack.length - 1].node;
      const node = { content: nestedMatch[1], children: [] };
      parent.children.push(node);
      stack.push({ level: 3, node });
      continue;
    }

    const deepMatch = line.match(/^    - (.+)/);
    if (deepMatch) {
      while (stack.length > 4) stack.pop();
      const parent = stack[stack.length - 1].node;
      const node = { content: deepMatch[1], children: [] };
      parent.children.push(node);
      stack.push({ level: 4, node });
      continue;
    }
  }

  return root;
}

function generateHtml(title, md, outputPath) {
  const tree = mdToTree(md);
  const escaped = JSON.stringify(tree);

  const html = '<!doctype html>\n<html>\n<head>\n<meta charset="UTF-8" />\n<meta name="viewport" content="width=device-width, initial-scale=1.0" />\n<meta http-equiv="X-UA-Compatible" content="ie=edge" />\n<title>' + title + '</title>\n<style>\n* { margin: 0; padding: 0; }\nhtml { font-family: ui-sans-serif, system-ui, sans-serif; }\n#mindmap { display: block; width: 100vw; height: 100vh; }\n.markmap-dark { background: #27272a; color: white; }\n</style>\n<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/markmap-toolbar@0.18.12/dist/style.css">\n</head>\n<body>\n<svg id="mindmap"></svg>\n<script src="https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js"></script><script src="https://cdn.jsdelivr.net/npm/markmap-view@0.18.12/dist/browser/index.js"></script><script src="https://cdn.jsdelivr.net/npm/markmap-toolbar@0.18.12/dist/index.js"></script><script>((r) => {\n          setTimeout(r);\n        })(() => {\n  const { markmap, mm } = window;\n  const toolbar = new markmap.Toolbar();\n  toolbar.attach(mm);\n  const el = toolbar.render();\n  el.setAttribute("style", "position:absolute;bottom:20px;right:20px");\n  document.body.append(el);\n})</script><script>((getMarkmap, getOptions, root2, jsonOptions) => {\n              const markmap = getMarkmap();\n              window.mm = markmap.Markmap.create(\n                "svg#mindmap",\n                (getOptions || markmap.deriveOptions)(jsonOptions),\n                root2\n              );\n              if (window.matchMedia("(prefers-color-scheme: dark)").matches) {\n                document.documentElement.classList.add("markmap-dark");\n              }\n            })(() => window.markmap,null,' + escaped + ',null)</script>\n</body>\n</html>';

  fs.writeFileSync(outputPath, html, 'utf-8');
  console.log('Generated:', outputPath);
}

const md1 = '# AI Agent 第1章 · Agent 概述\n\n## 核心公式\n- Agent = LLM + 上下文 + 工具\n- 大脑 + 眼睛 + 手脚\n- LLM: 理解意图、思考规划、做出判断\n- 上下文: 静态前缀 + 动态轨迹\n- 工具: 感知世界、执行操作\n\n## 观察空间与动作空间\n- 观察通道 → 模型能感知的信息\n- 动作接口 → 模型能执行的操作\n- 扩展眼睛和手脚是最主要的能力杠杆\n- Manus: 合并 Deep Research + Coding + Computer Use\n- OpenClaw: 本地优先，连接数字生活\n\n## 工具分类（五类）\n- 感知工具: 搜索、文件读取、API、数据库\n- 执行工具: 代码执行、文件操作、系统命令\n- 协作工具: 子Agent委托、人工确认、多Agent协调\n- 事件触发工具: 邮件、定时、Webhook\n- 用户沟通工具: 消息、语音、邮件\n\n## LLM: Agent 的大脑\n- 预训练 → 世界知识与语言能力\n- 后训练 → 固化决策策略\n- 内部思考: 行动前先规划推演\n- 模型即Agent: 工具调用内化为原生能力\n- Harness = 马具: 引导模型力量到正确方向\n- 三条学习路径\n  - 上下文适应（临场）\n  - 外部产物更新（可控积累）\n  - 模型参数更新（永久内化）\n\n## 上下文: Agent 的眼睛\n- 五大组成部分\n  - 系统提示词（岗位说明书）\n  - 工具定义（能力声明）\n  - 用户消息（任务输入）\n  - 模型回复（思考+内容+工具调用）\n  - 工具执行结果（闭环反馈）\n- 静态前缀: System Prompt + Tool Definitions\n- 动态轨迹: 交互历史持续增长\n- 消融实验: 去掉任何组件性能显著退化\n\n## ReAct 循环\n- 思考 → 行动 → 观察 → 循环\n- 轨迹 = 静态前缀 + 动态消息历史\n- 模型决策 → 框架执行 → 结果回传 → 再决策\n- 关键: 框架执行，模型只决策\n- 必须设置最大迭代次数\n\n## Harness 工程\n- Agent = Model + Harness\n- Harness 五功能\n  - Context（上下文）\n  - Tools（工具接口）\n  - Constrain（约束）\n  - Verify（验证）\n  - Correct（纠正）\n- 从"能做事"到"可靠地做事"\n- 工程范式演进\n  - 提示工程 → 上下文工程 → Harness工程\n  - → Loop工程 → Graph工程\n\n## 编排模式\n- 工作流: 确定性路径，预定义节点\n- 自主Agent: 动态决策，环境反馈驱动\n- 从简单到复杂: 先优化提示词，再工作流，最后自主Agent\n\n## 护栏与安全\n- 输入侧: 相关性、安全分类、内容审核、规则过滤\n- 执行侧: 工具风险评级\n- 输出侧: PII过滤、内容检查\n- 人工干预: 超过失败阈值 / 高风险操作';

const md2 = '# AI Agent 第2章 · 上下文工程\n\n## 核心命题\n- 上下文决定 Agent 能力的上限\n- 中等模型+好上下文 > 顶级模型+缺信息\n- 团队文档化是 AI 原生的前提\n\n## API 上下文结构\n- 消息列表（messages）是核心\n- 四种消息角色\n  - system: 系统提示词（最高优先级）\n  - user: 用户输入\n  - assistant: 模型回复（文本/tool_calls）\n  - tool: 工具执行结果\n- 单轮对话: system + user → assistant\n- 多轮工具调用: 带 tools 字段，ReAct 循环\n- Agent 框架核心 = 管理 messages 列表\n\n## KV Cache\n- 原理: 缓存已计算 token 的 K、V 向量\n- 新增 token 只算自身，复用缓存\n- 三条核心准则\n  - 系统提示词和工具定义定稿后别改\n  - 动态信息追加到末尾\n  - 使用标准 API 格式\n- 四种错误模式\n  - 动态系统提示词（时间戳写进 system）\n  - 动态用户配置\n  - 工具定义动态排序\n  - 滑动窗口对话历史\n- 最致命: 文本格式化（USER:/ASSISTANT:）\n- KV Cache vs Prompt Cache\n  - KV Cache: 推理内部，单次请求\n  - Prompt Cache: API层，跨请求\n  - 都依赖前缀不变性\n\n## Chat Template\n- API JSON → 模型 token 流\n- 特殊标记: <|im_start|>, <|im_end|>\n- 不同模型家族格式不同\n- 解释了为什么必须用标准 API 格式\n\n## 注意力机制\n- Query（查询）: 当前词发出的搜索请求\n- Key（键）: 每个词的标签\n- Value（值）: 每个词的内容\n- Q·K → 权重 → 加权 V\n- 注意力储存池（Attention Sink）\n  - 第一个 token 吸收 70%+ 权重\n  - softmax 强制权重和=100%\n- 位置偏好: 开头结尾权重高，中间被忽视\n- Lost in the Middle\n\n## 提示工程\n- 语气与风格: 人格设计\n- 结构化提示: XML + Markdown\n- 流程驱动 vs 规则堆砌\n- 业务规则细化: 产品经理深度参与\n- Few-shot 示例: 难以用规则描述时给例子\n- 工具定义设计: 边界、示例、性能提示\n\n## 提示注入\n- 本质: 外部内容伪装成系统指令\n- 三类攻击\n  - 直接注入: 用户消息嵌入指令\n  - 间接注入: 网页/文档隐藏指令\n  - 记忆注入: 持久化污染后续会话\n- 防御: 来源标记、结构化角色、输入清洗\n\n## Agent Skills\n- 渐进式披露（Progressive Disclosure）\n- 三层结构\n  - 元数据: name + description（路由条件+反例）\n  - 核心流程: SKILL.md 正文\n  - 细则: 子文档和脚本\n- 元数据目录在 system prompt\n- 完整指令按需加载到对话末尾\n- 兼容 KV Cache\n\n## Agent 状态栏\n- 理论基础: 上下文学习是检索而非推理\n- 状态栏五类信息\n  - 任务规划（TODO列表）\n  - 侧信道信息（时间、位置）\n  - 环境观察摘要\n  - 工具调用计数\n  - 系统状态\n- 关键原则\n  - 用代码维护，别用 LLM\n  - 别删除原始上下文\n  - 把准确率当生产指标\n- 两种更新实现: 持久追加 vs 每轮替换\n\n## 上下文压缩\n- 两个动机\n  - 长度和成本约束\n  - 提升思考质量（更深层）\n- 上下文腐化: 装得下但找不到\n- 六种策略\n  - 无压缩 → 溢出\n  - 个体摘要 → 碎片化\n  - 组合摘要 → 截断风险\n  - 上下文感知压缩 → 最优\n  - 带引用感知 → 可溯源\n  - 自适应窗口 → 最大化保留\n- 生产分层压缩（5层）\n- 隔离优于压缩: 子Agent上下文隔离\n- 压缩设计四原则\n  - 信息价值非均匀分布\n  - 语义完整性\n  - 任务相关性\n  - 压缩即理解';

const publicDir = path.join(__dirname, '..', 'public');
generateHtml('AI Agent 第1章 · 思维导图', md1, path.join(publicDir, 'Agent-第1章-思维导图.html'));
generateHtml('AI Agent 第2章 · 上下文工程', md2, path.join(publicDir, 'Agent-第2章-思维导图.html'));
