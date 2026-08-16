"""AI 出题 / 审题 / 入库（生成 → 校验 → 审核 → 入库）。

按详细设计拆分职责：
- generate_batch：生成 + 结构/业务校验（Question Agent）
- review_question：审核单题（Review Agent）
- save_questions：审核通过后入库
- generate_questions：给 /questions/generate 直接调用的便捷编排（内部走上面三个）
"""
from pydantic import ValidationError
from sqlalchemy.orm import Session

from models import User
from models.enums import QuestionSource, QuestionStatus, QuestionType
from repositories import knowledge_repository, question_option_repository, question_repository
from schemas.generation import (
    GeneratedQuestion,
    GenerationOutput,
    ReviewResult,
)
from schemas.question import QuestionOut, to_question_out
from services import access
from services.llm_service import LLMService, get_llm
from services.question_validator import validate_question

MAX_ATTEMPTS = 3  # 生成批次最多尝试 3 次（对应"审核失败最多重试 2 次"）

GENERATION_SYSTEM = """你是一名出题专家，根据给定课程知识点生成高质量练习题。
严格只输出 JSON，不要输出解释或多余文本。JSON 格式如下：
{
  "questions": [
    {
      "type": "single_choice",
      "content": "题干内容",
      "options": [{"option_key": "A", "content": "选项内容", "sort_order": 0}],
      "answer": "正确答案",
      "analysis": "答案解析",
      "difficulty": 2
    }
  ]
}
规则：
- type 可选 single_choice / multiple_choice / true_false / fill_blank / short_answer
- 选择题必填 options(>=2)；单选/多选 answer 填字母(如 "A" 或 "ABD")
- 判断填 true/false；填空/简答填文本
- difficulty 范围 1-5
"""

REVIEW_SYSTEM = """你是一名严格的题目审核员。审核题目质量，检查：
1) 答案是否正确；2) 题目与知识点是否匹配；3) 表述是否清晰无歧义；4) 选项是否合理；5) 难度是否恰当。
严格只输出 JSON，格式：
{"passed": true, "score": 0.0, "issues": ["问题描述"]}"""


def _generation_user_prompt(
    workbook_name: str,
    knowledge_name: str,
    question_type: QuestionType,
    count: int,
    difficulty: int,
    context: str,
) -> str:
    return (
        f"练习册：{workbook_name}\n"
        f"知识点：{knowledge_name}\n"
        f"题型：{question_type.value}\n"
        f"数量：{count}\n"
        f"难度：{difficulty}\n"
        f"参考资料：\n{context or '（无）'}\n"
    )


def _review_user_prompt(question: GeneratedQuestion, knowledge_name: str, context: str) -> str:
    return (
        f"知识点：{knowledge_name}\n"
        f"题目：{question.model_dump_json()}\n"
        f"参考资料：\n{context or '（无）'}\n"
    )


def resolve_knowledge_name(db: Session, knowledge_id: int | None) -> str:
    if knowledge_id is None:
        return "整体"
    node = knowledge_repository.get_by_id(db, knowledge_id)
    return node.name if node is not None else "整体"


def generate_batch(
    llm: LLMService,
    workbook_name: str,
    knowledge_name: str,
    question_type: QuestionType,
    count: int,
    difficulty: int,
    context: str,
) -> list[GeneratedQuestion]:
    """生成一批题目并做结构/业务校验，返回有效题目列表。"""
    raw = llm.generate_json(
        GENERATION_SYSTEM,
        _generation_user_prompt(
            workbook_name, knowledge_name, question_type, count, difficulty, context
        ),
    )
    try:
        output = GenerationOutput.model_validate(raw)
    except ValidationError:
        return []
    valid: list[GeneratedQuestion] = []
    for question in output.questions:
        if len(valid) >= count:
            break
        if question.type != question_type:
            continue  # 题型不符
        if validate_question(question):
            continue  # 业务校验失败
        valid.append(question)
    return valid


def review_question(
    llm: LLMService,
    question: GeneratedQuestion,
    knowledge_name: str,
    context: str,
) -> ReviewResult | None:
    """审核单道题，返回 ReviewResult；解析失败返回 None。"""
    try:
        raw = llm.generate_json(
            REVIEW_SYSTEM, _review_user_prompt(question, knowledge_name, context)
        )
        return ReviewResult.model_validate(raw)
    except (ValidationError, ValueError):
        return None


def save_questions(
    db: Session,
    workbook_id: int,
    knowledge_id: int | None,
    questions: list[GeneratedQuestion],
) -> list[QuestionOut]:
    """审核通过的题目入库（source=ai, status=approved）。"""
    saved: list[QuestionOut] = []
    for question in questions:
        q = question_repository.create(
            db,
            workbook_id=workbook_id,
            knowledge_id=knowledge_id,
            type=question.type,
            content=question.content,
            answer=question.answer,
            analysis=question.analysis,
            difficulty=question.difficulty,
            source=QuestionSource.ai,
            status=QuestionStatus.approved,
        )
        if question.options:
            question_option_repository.replace(db, q.id, question.options)
        options = question_option_repository.get_by_question_ids(db, [q.id])
        saved.append(to_question_out(q, options))
    return saved


def generate_preview(
    llm: LLMService,
    workbook_name: str,
    topic: str,
    question_type: QuestionType,
    count: int,
    difficulty: int,
    context: str,
) -> list[GeneratedQuestion]:
    """生成并审核题目预览，沿用专家 Pipeline 的最多 2 次重试且不入库。"""
    approved: list[GeneratedQuestion] = []
    for _ in range(MAX_ATTEMPTS):
        if len(approved) >= count:
            break
        batch = generate_batch(
            llm, workbook_name, topic, question_type, count, difficulty, context
        )
        for question in batch:
            result = review_question(llm, question, topic, context)
            if result is not None and result.passed:
                approved.append(question)
            if len(approved) >= count:
                break
    return approved


def generate_questions(
    db: Session,
    user: User,
    workbook_id: int,
    question_type: QuestionType,
    count: int,
    knowledge_id: int | None = None,
    difficulty: int = 1,
    context: str = "",
    llm: LLMService | None = None,
) -> list[QuestionOut]:
    """便捷编排：生成 → 审核 → 重试 → 入库（供 /questions/generate 直接使用）。"""
    workbook = access.get_owned_workbook(db, user, workbook_id)
    llm = llm or get_llm()
    knowledge_name = resolve_knowledge_name(db, knowledge_id)

    approved: list[GeneratedQuestion] = []
    for _ in range(MAX_ATTEMPTS):
        if len(approved) >= count:
            break
        batch = generate_batch(
            llm, workbook.name, knowledge_name, question_type, count, difficulty, context
        )
        for question in batch:
            if len(approved) >= count:
                break
            result = review_question(llm, question, knowledge_name, context)
            if result is not None and result.passed:
                approved.append(question)

    return save_questions(db, workbook_id, knowledge_id, approved)


def generate_similar(
    db: Session,
    user: User,
    question_id: int,
    llm: LLMService | None = None,
) -> GeneratedQuestion | None:
    """举一反三：针对某道题生成一道同类型练习题（不入库，返回给前端）。"""
    from repositories import question_repository

    question = question_repository.get_by_id(db, question_id)
    if question is None or question.deleted_at is not None:
        raise access.AccessError(404, "题目不存在")
    workbook = access.get_visible_workbook(db, user, question.workbook_id)
    llm = llm or get_llm()
    knowledge_name = resolve_knowledge_name(db, question.knowledge_id)
    context = (
        f"原题：{question.content}\n"
        f"答案：{question.answer}\n"
        f"解析：{question.analysis or ''}\n"
        f"总结：{question.summary or ''}"
    )
    batch = generate_batch(
        llm, workbook.name, knowledge_name, question.type, 1, question.difficulty, context
    )
    return batch[0] if batch else None
