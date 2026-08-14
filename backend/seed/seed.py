"""种子脚本：系统账号/工作簿 + 开发者账号 + 内置 Agent 题库（AI Agent 第 1-2 章）。

运行：cd backend && python -m seed.seed

行为：
- 确保系统账号（id=0）与系统工作簿（id=0）存在
- 确保开发者账号存在（dev / dev123456，仅用于本地测试）
- 清空系统工作簿的旧内置题与其知识节点（含关联答题/错题记录），重新灌入 agent_bank 题库
- 用户自建练习册与数据不受影响
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.engine import SessionLocal
from models import (
    AnswerRecord,
    Knowledge,
    Question,
    QuestionOption,
    ReviewCard,
    User,
    Workbook,
    WrongRecord,
)
from models.enums import QuestionSource, QuestionStatus, QuestionType
from seed.agent_bank import KNOWLEDGE_TREE, QUESTIONS
from services.security import hash_password

SYSTEM_USER_ID = 0
SYSTEM_WORKBOOK_ID = 0

DEV_USERNAME = "dev"
DEV_EMAIL = "dev@local"
DEV_PASSWORD = "dev123456"  # 仅本地测试用简单密码


def _ensure_system(session) -> None:
    if session.get(User, SYSTEM_USER_ID) is None:
        session.add(
            User(id=SYSTEM_USER_ID, username="system", email="system@local", password_hash="!")
        )
        session.flush()
    if session.get(Workbook, SYSTEM_WORKBOOK_ID) is None:
        session.add(
            Workbook(
                id=SYSTEM_WORKBOOK_ID,
                user_id=SYSTEM_USER_ID,
                name="内置题库",
                description="系统内置题库：《深入理解 AI Agent》第 1-2 章",
            )
        )
        session.flush()


def _ensure_dev_account(session) -> None:
    if session.query(User).filter(User.username == DEV_USERNAME).first() is not None:
        return
    session.add(
        User(
            username=DEV_USERNAME,
            email=DEV_EMAIL,
            password_hash=hash_password(DEV_PASSWORD),
        )
    )
    session.flush()


def _purge_builtin(session) -> int:
    """删除系统工作簿的旧内置题、知识节点及其关联学习记录，返回删除题数。"""
    question_ids = [
        qid
        for (qid,) in session.query(Question.id)
        .filter(Question.workbook_id == SYSTEM_WORKBOOK_ID)
        .all()
    ]
    if question_ids:
        # answer/wrong 记录对 question 为 RESTRICT，需先显式清理；review_cards 为 CASCADE 一并显式删
        session.query(WrongRecord).filter(WrongRecord.question_id.in_(question_ids)).delete(
            synchronize_session=False
        )
        session.query(AnswerRecord).filter(AnswerRecord.question_id.in_(question_ids)).delete(
            synchronize_session=False
        )
        session.query(ReviewCard).filter(ReviewCard.question_id.in_(question_ids)).delete(
            synchronize_session=False
        )
        session.query(QuestionOption).filter(QuestionOption.question_id.in_(question_ids)).delete(
            synchronize_session=False
        )
        session.query(Question).filter(Question.id.in_(question_ids)).delete(
            synchronize_session=False
        )
    session.query(Knowledge).filter(Knowledge.workbook_id == SYSTEM_WORKBOOK_ID).delete(
        synchronize_session=False
    )
    session.flush()
    return len(question_ids)


def _seed_agent_bank(session) -> tuple[int, int]:
    """灌入 Agent 题库，返回 (知识节点数, 题目数)。"""
    chapter_nodes: dict[str, int] = {}
    knowledge_nodes: dict[str, int] = {}
    for chapter, points in KNOWLEDGE_TREE:
        node = Knowledge(workbook_id=SYSTEM_WORKBOOK_ID, parent_id=None, name=chapter, level=0)
        session.add(node)
        session.flush()
        chapter_nodes[chapter] = node.id
        for point in points:
            child = Knowledge(
                workbook_id=SYSTEM_WORKBOOK_ID,
                parent_id=node.id,
                name=point,
                level=1,
            )
            session.add(child)
            session.flush()
            knowledge_nodes[point] = child.id

    inserted = 0
    for q in QUESTIONS:
        knowledge_id = knowledge_nodes.get(q["knowledge"]) or chapter_nodes.get(q["chapter"])
        question = Question(
            workbook_id=SYSTEM_WORKBOOK_ID,
            knowledge_id=knowledge_id,
            type=QuestionType(q["type"]),
            content=q["content"],
            answer=q["answer"],
            analysis=q.get("analysis"),
            difficulty=q.get("difficulty", 1),
            source=QuestionSource.builtin,
            status=QuestionStatus.approved,
        )
        session.add(question)
        session.flush()
        for sort_order, (key, content) in enumerate(q.get("options") or []):
            session.add(
                QuestionOption(
                    question_id=question.id,
                    option_key=key,
                    content=content,
                    sort_order=sort_order,
                )
            )
        inserted += 1
    return len(chapter_nodes) + len(knowledge_nodes), inserted


def main() -> None:
    session = SessionLocal()
    try:
        _ensure_system(session)
        _ensure_dev_account(session)
        purged = _purge_builtin(session)
        n_knowledge, n_questions = _seed_agent_bank(session)
        session.commit()
        print(
            f"seed 完成：清除旧内置题 {purged} 道；灌入 Agent 题库 {n_questions} 道、"
            f"知识节点 {n_knowledge} 个；开发者账号 {DEV_USERNAME} / {DEV_PASSWORD}。"
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
