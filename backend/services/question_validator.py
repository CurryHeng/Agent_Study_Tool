"""出题的业务校验（确定性规则，与 LLM 语义判断分离）。

对应详细设计 Pt.3 §15 的「业务校验」层。
"""
from models.enums import CHOICE_TYPES, QuestionType
from schemas.generation import GeneratedQuestion

_LETTER_TYPES = {QuestionType.single_choice, QuestionType.multiple_choice}


def validate_question(question: GeneratedQuestion) -> list[str]:
    """返回问题列表（空 = 通过业务校验）。"""
    issues: list[str] = []

    if question.type in CHOICE_TYPES and len(question.options) < 2:
        issues.append("选择题选项少于 2 个")

    if question.type in _LETTER_TYPES:
        keys = [o.option_key for o in question.options]
        if keys and any(ch not in keys for ch in question.answer):
            issues.append(f"答案 '{question.answer}' 不在选项 {keys} 中")

    if question.type not in CHOICE_TYPES and question.options:
        issues.append("非选择题不应携带选项")

    return issues
