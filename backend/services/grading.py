"""程序自动判题 + 简答题 LLM 判分。

判题基于结构化 Question / QuestionOption：
- single_choice：答案字母相等
- multiple_choice：答案字母集合相等
- true_false：布尔值归一化后相等
- fill_blank：文本归一化后相等
- short_answer：LLM 判分（grade_short_answer），LLM 不可用时降级为不自动判题
"""
from models.enums import CHOICE_TYPES, QuestionType
from models.question import Question

# 可确定性自动判题的题型 = 选择题型 + 填空题（简答题需 LLM，见 grade_short_answer）
AUTO_GRADABLE = frozenset(CHOICE_TYPES | {QuestionType.fill_blank})

_TRUE_VALUES = {"true", "t", "1", "正确", "对", "是", "yes", "y"}
_FALSE_VALUES = {"false", "f", "0", "错误", "错", "否", "no", "n"}

SHORT_ANSWER_SYSTEM = """你是一名严格的判题老师，判断学生对简答题的作答是否正确。
根据题目与参考答案评估：要点覆盖、语义一致即可判对，不要求逐字相同；答非所问或要点缺失判错。
只输出 JSON，格式：{"correct": true} 或 {"correct": false}"""


def is_auto_gradable(question_type: QuestionType) -> bool:
    return question_type in AUTO_GRADABLE


def _choice(answer: str | None) -> str:
    return (answer or "").strip().upper()


def _bool(value: str | None) -> str:
    v = (value or "").strip().lower()
    if v in _TRUE_VALUES:
        return "true"
    if v in _FALSE_VALUES:
        return "false"
    return v


def _text(value: str | None) -> str:
    return (value or "").strip().lower()


def grade_question(question: Question, user_answer: str | None) -> bool:
    question_type = question.type
    if question_type == QuestionType.single_choice:
        return _choice(user_answer) == _choice(question.answer)
    if question_type == QuestionType.multiple_choice:
        return set(_choice(user_answer)) == set(_choice(question.answer))
    if question_type == QuestionType.true_false:
        return _bool(user_answer) == _bool(question.answer)
    if question_type == QuestionType.fill_blank:
        return _text(user_answer) == _text(question.answer)
    return False  # short_answer 不走确定性判题，用 grade_short_answer


def grade_short_answer(question: Question, user_answer: str | None, llm=None) -> bool | None:
    """LLM 判简答题（P1 AnswerEvaluation）。

    - 未作答/空白：直接判错（不调用 LLM）；
    - LLM 未配置/调用失败/输出无法解析：返回 None，降级为不自动判题（前端转为用户自评）。
    """
    if not (user_answer or "").strip():
        return False
    if llm is None:
        from services.llm_service import get_llm

        llm = get_llm()
    prompt = (
        f"题目：{question.content}\n"
        f"参考答案：{question.answer}\n"
        f"学生作答：{user_answer.strip()}"
    )
    try:
        raw = llm.generate_json(SHORT_ANSWER_SYSTEM, prompt)
        return bool(raw.get("correct"))
    except Exception:
        return None
