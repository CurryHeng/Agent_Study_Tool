"""程序自动判题 + 填空题/简答题 LLM 判分。

判题基于结构化 Question / QuestionOption：
- single_choice：答案字母相等
- multiple_choice：答案字母集合相等
- true_false：布尔值归一化后相等
- fill_blank：先精确匹配，否则 LLM 判近义（grade_fill_blank），LLM 不可用降级为精确匹配
- short_answer：LLM 判分（grade_short_answer），LLM 不可用时降级为不自动判题
"""
from models.enums import CHOICE_TYPES, QuestionType
from models.question import Question

# 可确定性自动判题的题型 = 选择题型 + 填空题（简答题需 LLM，见 grade_short_answer）
AUTO_GRADABLE = frozenset(CHOICE_TYPES | {QuestionType.fill_blank})

_TRUE_VALUES = {"true", "t", "1", "正确", "正确的", "对", "对的", "是", "是的", "yes", "y"}
_FALSE_VALUES = {"false", "f", "0", "错误", "错误的", "错", "错的", "不对", "否", "不是", "no", "n"}

SHORT_ANSWER_SYSTEM = """你是一名严格的判题老师，判断学生对简答题的作答是否正确。
根据题目与参考答案评估：要点覆盖、语义一致即可判对，不要求逐字相同；答非所问或要点缺失判错。
只输出 JSON，格式：{"correct": true} 或 {"correct": false}"""

FILL_BLANK_SYSTEM = """你是一名严格的填空题判题老师，判断学生的填空答案是否与参考答案等价。
以下情况判对（correct=true）：
- 与参考答案文字一致；
- 同一概念的不同表述、简称、近义词（如"反向传播算法"与"BP算法"、"误差反向传播"）；
- 参考答案含多个可接受答案（用 / 或 ；等分隔）时，学生答出其中任意一个。
答非所问、含义不同、张冠李戴判错（correct=false）。
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


def grade_fill_blank(question: Question, user_answer: str | None, llm=None) -> bool:
    """填空题判分（P1-8 多答案/近义）：精确匹配 → LLM 近义判分 → 降级为精确匹配结果。

    - 空白作答：直接判错（不调用 LLM）；
    - 精确匹配（忽略空白与大小写）：判对，不调用 LLM；
    - 非空但不匹配：调用 LLM 判近义；LLM 判对 → True；LLM 判错/未配置/调用失败 → False（降级）。
    """
    if not (user_answer or "").strip():
        return False
    if _text(user_answer) == _text(question.answer):
        return True
    if llm is None:
        from services.llm_service import get_llm

        llm = get_llm()
    prompt = (
        f"题目：{question.content}\n"
        f"参考答案：{question.answer}\n"
        f"学生作答：{user_answer.strip()}"
    )
    try:
        raw = llm.generate_json(FILL_BLANK_SYSTEM, prompt)
        return bool(raw.get("correct"))
    except Exception:
        return False


def grade_answer(question: Question, user_answer: str | None):
    """对所有题型统一判分（供答题/单独判分复用）。

    - 选择/判断：确定性判题；
    - 填空：精确匹配 → LLM 近义判分，LLM 不可用降级为精确匹配；
    - 简答：LLM 判分，LLM 不可用返回 None（降级为用户自评）。
    """
    if question.type == QuestionType.fill_blank:
        return grade_fill_blank(question, user_answer)
    if is_auto_gradable(question.type):
        return grade_question(question, user_answer)
    if question.type == QuestionType.short_answer:
        return grade_short_answer(question, user_answer)
    return None
