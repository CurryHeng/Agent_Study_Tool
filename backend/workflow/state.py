"""TaskState：LangGraph 各节点共享的统一任务状态（对齐详细设计 Pt.1 §2.2）。

字段说明（course_id 在本项目改名为 workbook_id）：
- 身份：task_id / user_id / workbook_id
- 请求：user_request / intent / params
- 规划：task_plan / current_step
- 知识：document_ids / knowledge_ids / retrieved_context
- Agent 产出：generated_data / review_result
- 权限/错误/结果：permission / errors / retry_count / final_result

读写边界（Pt.1 §3）：
- Navigator：写 intent / task_plan / params / current_step
- Orchestrator：读 task_plan，写 current_step
- Question Agent：读 params，写 generated_data
- Review Agent：读 generated_data，写 review_result / generated_data
- Result Handler：写 final_result
"""
from typing import TypedDict


class TaskState(TypedDict, total=False):
    task_id: str
    user_id: int
    workbook_id: int | None
    user_request: str
    intent: str
    params: dict
    task_plan: list[str]
    current_step: str
    document_ids: list[int]
    knowledge_ids: list[int]
    retrieved_context: str
    generated_data: dict
    review_result: dict
    permission: dict
    errors: list
    retry_count: int
    final_result: dict
