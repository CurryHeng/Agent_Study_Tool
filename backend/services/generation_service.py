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
    GenerateResult,
    GenerationOutput,
    RejectedQuestion,
    ReviewResult,
)
from schemas.question import QuestionOut, to_question_out
from services import access
from services.llm_service import LLMService, get_llm
from services.question_validator import validate_question

MAX_ATTEMPTS = 3  # 生成批次最多尝试 3 次（对应"审核失败最多重试 2 次"）

# 生成与审核的采样温度：生成略高以增加多样性、打散答案位置；审核取 0 保证判定稳定。
GENERATION_TEMPERATURE = 0.8
REVIEW_TEMPERATURE = 0.0

# 审题通过的最低质量分（0~1）。LLM 判定 passed 但评分过低时视为驳回，防止错题漏网。
PASS_SCORE_THRESHOLD = 0.5

GENERATION_SYSTEM = """你是一名出题专家，根据给定的课程知识点与参考资料，生成高质量练习题。

【硬性要求】
- 严格只输出 JSON，不要输出解释或多余文本。
- 题目必须基于参考资料，不得凭空编造与资料无关的内容。
- 每道题独立、完整、无歧义，可脱离上下文单独作答。
- 避免生成彼此高度重复的题目，尽量覆盖知识点的不同侧面。

【输出格式】
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

【各题型规则】
- single_choice（单选）：options 至少 4 个，且必须恰好只有一个正确选项；
  answer 填该选项字母（如 "A"）。
- multiple_choice（多选）：options 至少 4 个，至少 2 个正确选项；
  answer 填多个字母（如 "ABD"，按字母序）。
- true_false（判断）：题干为一句可判真假的陈述；answer 填 "true" 或 "false"；不要 options。
- fill_blank（填空）：题干中用 ____ 标出空位；answer 填标准答案文本；不要 options。
- short_answer（简答）：题干为开放式问题；answer 填参考答案要点；不要 options。

【答案分布（单选）】
- 单选题正确答案的字母必须均匀分布在 A/B/C/D 之间，不得集中或全为同一字母。

【难度】
- difficulty 取 1-5：1=记忆型基础题，2=理解题，3=应用题，4=分析题，5=综合难题。
- 严格按请求的难度值出题；干扰项要有迷惑性，但不能出现第二个正确答案。
"""

REVIEW_SYSTEM = """你是一名严格的题目审核员。逐项审核题目质量，只有完全合格才判通过。

【审核清单】
1. 答案正确性：答案是否事实正确，是否与参考资料一致。
2. 答案格式：选择题答案字母必须存在于选项中；单选必须恰好一个正确选项，
   多选至少两个；判断题答案必须是 true/false。
3. 唯一性：单选题不得出现多个正确选项；干扰项不得与正确答案冲突。
4. 表述清晰：题干无歧义、无残缺，可独立作答。
5. 难度恰当：标注难度与实际难度相符。

【判定规则（务必严格遵守）】
- 存在以下任一硬伤 → passed=false，issues 必须逐条写明具体问题：
  a) 答案事实错误或与参考资料矛盾；
  b) 选择题答案字母不在选项中；单选题有多个正确选项；多选正确选项不足两个；
  c) 题干有歧义或残缺，无法独立作答；
  d) 难度标注严重不符。
- 无任何硬伤 → passed=true，issues 返回空数组 []（不要写建议）。
- score 为 0.0~1.0 的质量分：1.0 完美，0.6 及格；无硬伤时 score >= 0.6。

严格只输出 JSON，不要多余文本：
{"passed": true, "score": 0.85, "issues": []}"""


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
        temperature=GENERATION_TEMPERATURE,
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
    """审核单道题，返回 ReviewResult；解析失败返回 None。

    判定以 LLM 的 passed 为准，另加评分阈值兜底：LLM 判 passed 但 score
    低于 PASS_SCORE_THRESHOLD 时视为驳回，避免错题漏网。
    """
    try:
        raw = llm.generate_json(
            REVIEW_SYSTEM,
            _review_user_prompt(question, knowledge_name, context),
            temperature=REVIEW_TEMPERATURE,
        )
        result = ReviewResult.model_validate(raw)
    except (ValidationError, ValueError):
        return None
    result.score = max(0.0, min(1.0, result.score))
    if result.passed and result.score < PASS_SCORE_THRESHOLD:
        result.passed = False
        if not result.issues:
            result.issues = ["审题评分过低"]
    return result


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


def _generate_and_review(
    llm: LLMService,
    workbook_name: str,
    knowledge_name: str,
    question_type: QuestionType,
    count: int,
    difficulty: int,
    context: str,
) -> tuple[list[GeneratedQuestion], list[tuple[GeneratedQuestion, ReviewResult]]]:
    """生成 → 审题 主循环（最多 MAX_ATTEMPTS 轮）。

    返回 (approved, rejected)：approved 为通过审题的题目；rejected 为
    (题目, 审题结果) 的驳回项，含未通过原因，供前端展示审题结果。
    """
    approved: list[GeneratedQuestion] = []
    rejected: list[tuple[GeneratedQuestion, ReviewResult]] = []
    for _ in range(MAX_ATTEMPTS):
        if len(approved) >= count:
            break
        batch = generate_batch(
            llm, workbook_name, knowledge_name, question_type, count, difficulty, context
        )
        for question in batch:
            if len(approved) >= count:
                break
            result = review_question(llm, question, knowledge_name, context)
            if result is not None and result.passed:
                approved.append(question)
            else:
                review = result or ReviewResult(
                    passed=False, score=0.0, issues=["审题结果解析失败"]
                )
                rejected.append((question, review))
    return approved, rejected


def generate_questions_with_review(
    db: Session,
    user: User,
    workbook_id: int,
    question_type: QuestionType,
    count: int,
    knowledge_id: int | None = None,
    difficulty: int = 1,
    context: str = "",
    llm: LLMService | None = None,
) -> GenerateResult:
    """生成 → 审题 → 入库，返回入库题目与驳回原因（供 /questions/generate 展示审题结果）。"""
    workbook = access.get_owned_workbook(db, user, workbook_id)
    llm = llm or get_llm()
    knowledge_name = resolve_knowledge_name(db, knowledge_id)

    approved, rejected = _generate_and_review(
        llm, workbook.name, knowledge_name, question_type, count, difficulty, context
    )
    saved = save_questions(db, workbook_id, knowledge_id, approved)
    return GenerateResult(
        saved=saved,
        rejected=[
            RejectedQuestion(question=question, review=review)
            for question, review in rejected
        ],
    )


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
    """便捷编排：生成 → 审核 → 重试 → 入库（兼容旧签名，返回入库题目列表）。"""
    return generate_questions_with_review(
        db, user, workbook_id, question_type, count, knowledge_id, difficulty, context, llm
    ).saved


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
