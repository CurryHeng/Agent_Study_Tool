"""助手·导师主 Agent：唯一开放式 ReAct 决策入口。"""
from langgraph.prebuilt import create_react_agent

from services.llm_service import get_llm
from workflow.tools import build_tools

MAX_ITERATIONS = 8
RECURSION_LIMIT = MAX_ITERATIONS * 2 + 1

SUPERVISOR_PROMPT = """你是 EStudy 的助手·导师，是系统唯一的开放式任务决策入口。
根据用户目标自主选择工具；需要资料依据时先检索，再完成任务。
请求中若提供当前页面或选中实体上下文，用户所说“这里”“这个”优先指向该实体。
结合已有多轮消息理解省略表达，例如“再来 5 道难的”应沿用上一轮主题。
工具参数必须具体，尤其 generate_questions 的 topic 必须来自用户主题或检索结果。
所有写工具只返回待确认提案；明确告诉用户确认前不会写入或删除数据。
用户要求新增、修改、删除或生成数据时，必须调用对应写工具生成结构化 proposal；
禁止只在自然语言回复中模拟提案，也不要让用户通过回复“确认”来代替确认卡片。
不要执行 SQL、文件或系统命令。最多调用工具 8 次。
最后用中文简洁说明结果；若工具失败，诚实说明失败原因。
"""


def build_graph(db, user, llm=None, tools=None, agent_factory=None):
    """构建单次请求使用的 ReAct supervisor。依赖参数便于 mock 测试。"""
    llm_service = llm or get_llm()
    tool_list = tools if tools is not None else build_tools(db, user, llm_service)
    factory = agent_factory or create_react_agent
    return factory(
        model=llm_service.chat_model(),
        tools=tool_list,
        prompt=SUPERVISOR_PROMPT,
    )
