"""LangGraph 工作流（对齐详细设计 Pt.1/Pt.2）：

START → Navigator → Orchestrator → 专业 Agent → Review → Result Handler → END

- Navigator：理解意图，产出 task_plan（任务步骤）
- Orchestrator：按 task_plan 决定下一执行节点（独立节点）
- Question Agent：生成题目（复用 generation_service.generate_batch）
- Review Agent：审核题目（复用 generation_service.review_question），FAIL 回环重试（最多 2 次）
"""
from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from schemas.generation import GeneratedQuestion
from services import (
    access,
    generation_service,
    mindmap_service,
    rag_service,
)
from services.llm_service import get_llm
from workflow.state import TaskState

VALID_INTENTS = {"generate_questions", "generate_mindmap", "list_documents", "chat"}
MAX_RETRIES = 2  # 审核失败最多重试 2 次（共 3 次尝试）

INTENT_PLAN: dict[str, list[str]] = {
    "generate_questions": ["question_agent", "review_agent"],
    "generate_mindmap": ["mindmap_agent"],
    "list_documents": ["document_agent"],
    "chat": ["direct_answer"],
}

NAVIGATOR_SYSTEM = """你是 StudyForge 的任务导航器，理解用户意图并确定任务类型。
只输出 JSON，格式：
{
  "intent": "generate_questions | generate_mindmap | list_documents | chat",
  "params": {
    "workbook_id": 1,
    "question_type": "single_choice",
    "count": 5,
    "difficulty": 1,
    "knowledge_id": null
  }
}
params 按任务类型填对应字段，未提及的字段省略。"""

DIRECT_REPLY = "我是 StudyForge 助手，可以帮你生成题目、生成思维导图、整理资料。"

CHAT_SYSTEM = """你是 StudyForge 学习助手，友好、简洁地解答用户关于学习、刷题、复习、AI 出题的问题。
只输出 JSON，格式：{"reply": "你的回答"}"""


def _parse_navigation(raw: dict) -> dict:
    intent = raw.get("intent", "chat")
    if intent not in VALID_INTENTS:
        intent = "chat"
    params = raw.get("params") or {}
    if not isinstance(params, dict):
        params = {}
    return {"intent": intent, "params": params}


def _require_workbook_id(params: dict) -> int:
    """取练习册 ID，缺失时友好报错（避免 LLM 未返回时 KeyError → 500）。"""
    workbook_id = params.get("workbook_id")
    if workbook_id is None:
        raise access.AccessError(400, "请先指定要操作的练习册（workbook_id）")
    return workbook_id


def build_graph(
    db,
    user,
    navigator_llm=None,
    generate_fn=None,
    review_fn=None,
    save_fn=None,
    workbook_hint=None,
):
    nav_llm = navigator_llm or get_llm()
    llm = get_llm()

    if generate_fn is None:

        def generate_fn(params):
            workbook = access.get_visible_workbook(db, user, _require_workbook_id(params))
            knowledge_name = generation_service.resolve_knowledge_name(
                db, params.get("knowledge_id")
            )
            context = rag_service.build_context(
                db, user, params["workbook_id"], params.get("knowledge_id")
            )
            return generation_service.generate_batch(
                llm,
                workbook.name,
                knowledge_name,
                params.get("question_type", "single_choice"),
                params.get("count", 5),
                params.get("difficulty", 1),
                context,
            )

    if review_fn is None:

        def review_fn(question, params):
            knowledge_name = generation_service.resolve_knowledge_name(
                db, params.get("knowledge_id")
            )
            context = rag_service.build_context(
                db, user, params.get("workbook_id"), params.get("knowledge_id")
            )
            result = generation_service.review_question(llm, question, knowledge_name, context)
            return result is not None and result.passed

    if save_fn is None:

        def save_fn(params, questions):
            return generation_service.save_questions(
                db, _require_workbook_id(params), params.get("knowledge_id"), questions
            )

    # ── Navigator：意图 → task_plan ──
    def navigator(state: TaskState) -> dict:
        raw = nav_llm.generate_json(NAVIGATOR_SYSTEM, state["user_request"])
        nav = _parse_navigation(raw)
        params = dict(nav["params"])
        if workbook_hint is not None and "workbook_id" not in params:
            params["workbook_id"] = workbook_hint
        return {
            "intent": nav["intent"],
            "params": params,
            "task_plan": INTENT_PLAN[nav["intent"]],
            "current_step": "navigator",
        }

    # ── Orchestrator：按 task_plan 决定下一节点 ──
    def orchestrator(state: TaskState) -> dict:
        plan = state.get("task_plan", [])
        step = plan[0] if plan else "result_handler"
        return {"current_step": step}

    # ── Question Agent：生成（不做审核）──
    def question_agent(state: TaskState) -> dict:
        params = state["params"]
        raw = generate_fn(params)
        questions: list[GeneratedQuestion] = []
        for item in raw:
            if isinstance(item, GeneratedQuestion):
                questions.append(item)
            else:
                try:
                    questions.append(GeneratedQuestion.model_validate(item))
                except ValidationError:
                    continue
        return {
            "generated_data": {"questions": questions},
            "retry_count": state.get("retry_count", 0) + 1,
            "current_step": "question_agent",
        }

    # ── Review Agent：审核 + 入库 ──
    def review_agent(state: TaskState) -> dict:
        params = state["params"]
        questions = state.get("generated_data", {}).get("questions", [])
        approved = [q for q in questions if review_fn(q, params)]
        saved = save_fn(params, approved)
        return {
            "generated_data": {"approved": saved},
            "review_result": {"total": len(questions), "passed": len(approved)},
            "current_step": "review_agent",
        }

    def mindmap_agent(state: TaskState) -> dict:
        workbook = access.get_visible_workbook(db, user, _require_workbook_id(state["params"]))
        mindmap = mindmap_service.build_mindmap(db, workbook)
        return {
            "generated_data": {"mindmap": mindmap.model_dump()},
            "current_step": "mindmap_agent",
        }

    def document_agent(state: TaskState) -> dict:
        from services import document_service

        docs = document_service.list_documents(db, user, _require_workbook_id(state["params"]))
        return {
            "generated_data": {"documents": [d.model_dump() for d in docs]},
            "current_step": "document_agent",
        }

    def direct_answer(state: TaskState) -> dict:
        try:
            raw = nav_llm.generate_json(CHAT_SYSTEM, state["user_request"])
            reply = raw.get("reply") if isinstance(raw, dict) else None
        except Exception:
            reply = None
        return {
            "generated_data": {"reply": reply or DIRECT_REPLY},
            "current_step": "direct_answer",
        }

    def result_handler(state: TaskState) -> dict:
        intent = state["intent"]
        data = state.get("generated_data", {})
        if intent == "generate_questions":
            final = {"intent": intent, "questions": data.get("approved", [])}
        elif intent == "generate_mindmap":
            final = {"intent": intent, "mindmap": data.get("mindmap")}
        elif intent == "list_documents":
            final = {"intent": intent, "documents": data.get("documents", [])}
        else:
            final = {"intent": intent, "reply": data.get("reply", "")}
        return {"final_result": final, "current_step": "result_handler"}

    def route_after_orchestrator(state: TaskState) -> str:
        return state["current_step"]

    def route_after_review(state: TaskState) -> str:
        approved = state.get("generated_data", {}).get("approved", [])
        if not approved and state.get("retry_count", 0) <= MAX_RETRIES:
            return "question_agent"
        return "result_handler"

    graph = StateGraph(TaskState)
    graph.add_node("navigator", navigator)
    graph.add_node("orchestrator", orchestrator)
    graph.add_node("question_agent", question_agent)
    graph.add_node("review_agent", review_agent)
    graph.add_node("mindmap_agent", mindmap_agent)
    graph.add_node("document_agent", document_agent)
    graph.add_node("direct_answer", direct_answer)
    graph.add_node("result_handler", result_handler)

    graph.add_edge(START, "navigator")
    graph.add_edge("navigator", "orchestrator")
    graph.add_conditional_edges(
        "orchestrator",
        route_after_orchestrator,
        {
            "question_agent": "question_agent",
            "mindmap_agent": "mindmap_agent",
            "document_agent": "document_agent",
            "direct_answer": "direct_answer",
            "result_handler": "result_handler",
        },
    )
    graph.add_edge("question_agent", "review_agent")
    graph.add_conditional_edges(
        "review_agent",
        route_after_review,
        {"question_agent": "question_agent", "result_handler": "result_handler"},
    )
    graph.add_edge("mindmap_agent", "result_handler")
    graph.add_edge("document_agent", "result_handler")
    graph.add_edge("direct_answer", "result_handler")
    graph.add_edge("result_handler", END)

    return graph.compile()
