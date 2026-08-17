"""错因分析（教练专家 v1）：读错题 + 作答记录 → LLM 结构化归因。

输出 {reason_type, explanation, suggestion}，落库到 wrong_records 的错因字段。
reason_type 枚举见 models.enums.REASON_TYPES（P1-1 契约 3，成员不得改动）。
"""
from sqlalchemy.orm import Session

from models import User
from models.enums import REASON_TYPES
from repositories import (
    answer_record_repository,
    question_repository,
    wrong_record_repository,
)
from schemas.wrong_record import WrongReasonAnalysis
from services import access
from services.llm_service import LLMService

REASON_TYPE_LIST = " / ".join(sorted(REASON_TYPES))

ANALYZE_SYSTEM = """你是一名学习教练，分析学生答错某道题的主要原因。
根据题目、正确答案、解析、学生的错误作答及近期作答历史，判断最主要的错因类型，并给出解释与改进建议。
reason_type 必须从这些值里选：概念不清、记忆遗忘、审题偏差、计算失误、方法不当、其他。
只输出 JSON，格式：
{"reason_type": "概念不清", "explanation": "归因解释", "suggestion": "改进建议"}"""


def _format_history(history) -> str:
    parts = []
    for h in history:
        if h.is_correct == 1:
            mark = "对"
        elif h.is_correct == 0:
            mark = "错"
        else:
            mark = "?"
        parts.append(f"{mark}:{h.user_answer or ''}")
    return "；".join(parts) or "（无作答历史）"


def _build_prompt(question, record, history) -> str:
    lines = [
        f"题目：{question.content if question else ''}",
        f"正确答案：{question.answer if question else ''}",
    ]
    if question is not None and question.analysis:
        lines.append(f"解析：{question.analysis}")
    lines.append(f"学生错误作答：{record.wrong_answer or '（未记录）'}")
    lines.append(f"近期作答历史：{_format_history(history)}")
    return "\n".join(lines)


def analyze_wrong_reason(
    db: Session,
    user: User,
    record_id: int,
    llm: LLMService | None = None,
) -> WrongReasonAnalysis:
    """对一条错题记录做 AI 归因，落库并返回结构化结果。"""
    record = wrong_record_repository.get_by_id(db, record_id)
    if record is None:
        raise access.AccessError(404, "错题记录不存在")
    if record.user_id != user.id:
        raise access.AccessError(403, "无权操作该错题记录")

    question = question_repository.get_by_id(db, record.question_id)
    history = answer_record_repository.list_by_question_user(
        db, record.question_id, user.id
    )

    if llm is None:
        from services.llm_service import get_llm

        llm = get_llm()
    try:
        raw = llm.generate_json(ANALYZE_SYSTEM, _build_prompt(question, record, history))
    except access.AccessError:
        raise  # LLM 未配置 → 503 友好提示
    except Exception:
        raise access.AccessError(500, "错因分析失败，请稍后重试") from None

    if not isinstance(raw, dict):
        raw = {}
    reason_type = raw.get("reason_type") if raw.get("reason_type") in REASON_TYPES else "其他"
    explanation = str(raw.get("explanation") or "").strip()
    suggestion = str(raw.get("suggestion") or "").strip()

    record.reason_type = reason_type
    record.ai_explanation = explanation
    record.ai_suggestion = suggestion
    db.flush()

    return WrongReasonAnalysis(
        reason_type=reason_type,
        explanation=explanation,
        suggestion=suggestion,
    )
