"""数据模型约束 / 外键删除行为 / 软删除 测试。"""
from datetime import UTC, date

import pytest
from sqlalchemy.exc import IntegrityError

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


def _mk_user(session, username="alice", email="alice@example.com"):
    u = User(username=username, email=email, password_hash="hash")
    session.add(u)
    session.flush()
    return u


def _mk_workbook(session, user, name="练习册A"):
    wb = Workbook(user_id=user.id, name=name)
    session.add(wb)
    session.flush()
    return wb


def _mk_question(session, workbook, type_=QuestionType.single_choice, answer="A"):
    q = Question(
        workbook_id=workbook.id,
        type=type_,
        content="题干",
        answer=answer,
        source=QuestionSource.builtin,
        status=QuestionStatus.approved,
    )
    session.add(q)
    session.flush()
    return q


# ── 唯一约束 ──────────────────────────────────────────────
def test_username_unique(session):
    _mk_user(session, username="alice")
    with pytest.raises(IntegrityError):
        _mk_user(session, username="alice", email="other@example.com")


def test_email_unique(session):
    _mk_user(session, email="dup@example.com")
    with pytest.raises(IntegrityError):
        _mk_user(session, username="bob", email="dup@example.com")


# ── CASCADE ───────────────────────────────────────────────
def test_question_option_cascade_on_question_delete(session):
    u = _mk_user(session)
    wb = _mk_workbook(session, u)
    q = _mk_question(session, wb)
    session.add(QuestionOption(question_id=q.id, option_key="A", content="选项", sort_order=0))
    session.flush()

    session.delete(q)
    session.flush()
    assert session.query(QuestionOption).count() == 0


def test_review_card_cascade_on_question_delete(session):
    u = _mk_user(session)
    wb = _mk_workbook(session, u)
    q = _mk_question(session, wb)
    session.add(ReviewCard(question_id=q.id, user_id=u.id, next_review=date.today()))
    session.flush()

    session.delete(q)
    session.flush()
    assert session.query(ReviewCard).count() == 0


def test_workbook_cascade_deletes_questions(session):
    u = _mk_user(session)
    wb = _mk_workbook(session, u)
    _mk_question(session, wb)

    session.delete(wb)
    session.flush()
    assert session.query(Question).count() == 0


def test_user_cascade_deletes_workbooks(session):
    u = _mk_user(session)
    wb = _mk_workbook(session, u)

    session.delete(u)
    session.flush()
    assert session.query(Workbook).filter(Workbook.id == wb.id).count() == 0


# ── RESTRICT（不可变历史，禁止静默丢失）────────────────────
def test_answer_record_restrict_blocks_question_delete(session):
    u = _mk_user(session)
    wb = _mk_workbook(session, u)
    q = _mk_question(session, wb)
    session.add(AnswerRecord(user_id=u.id, question_id=q.id, user_answer="B", is_correct=0))
    session.flush()

    with pytest.raises(IntegrityError):
        session.delete(q)
        session.flush()


def test_wrong_record_restrict_blocks_question_delete(session):
    u = _mk_user(session)
    wb = _mk_workbook(session, u)
    q = _mk_question(session, wb)
    session.add(WrongRecord(user_id=u.id, question_id=q.id, wrong_answer="B", wrong_reason="粗心"))
    session.flush()

    with pytest.raises(IntegrityError):
        session.delete(q)
        session.flush()


# ── SET NULL ──────────────────────────────────────────────
def test_knowledge_parent_set_null(session):
    u = _mk_user(session)
    wb = _mk_workbook(session, u)
    parent = Knowledge(workbook_id=wb.id, parent_id=None, name="第一章", level=0)
    session.add(parent)
    session.flush()
    child = Knowledge(workbook_id=wb.id, parent_id=parent.id, name="函数", level=1)
    session.add(child)
    session.flush()

    session.delete(parent)
    session.flush()
    session.expire_all()
    assert session.get(Knowledge, child.id).parent_id is None


def test_question_knowledge_set_null(session):
    u = _mk_user(session)
    wb = _mk_workbook(session, u)
    k = Knowledge(workbook_id=wb.id, parent_id=None, name="第一章", level=0)
    session.add(k)
    session.flush()
    q = _mk_question(session, wb)
    q.knowledge_id = k.id
    session.flush()

    session.delete(k)
    session.flush()
    session.expire_all()
    assert session.get(Question, q.id).knowledge_id is None


# ── 软删除 ────────────────────────────────────────────────
def test_soft_delete_hides_question_from_query(session):
    u = _mk_user(session)
    wb = _mk_workbook(session, u)
    q = _mk_question(session, wb)

    from datetime import datetime

    q.deleted_at = datetime.now(UTC)
    session.flush()

    visible = session.query(Question).filter(Question.deleted_at.is_(None)).count()
    assert visible == 0


# ── 复合主键（一人一题一卡）────────────────────────────────
def test_review_card_composite_pk_unique(session):
    u = _mk_user(session)
    wb = _mk_workbook(session, u)
    q = _mk_question(session, wb)
    session.add(ReviewCard(question_id=q.id, user_id=u.id, next_review=date.today()))
    session.flush()

    with pytest.raises(IntegrityError):
        session.add(ReviewCard(question_id=q.id, user_id=u.id, next_review=date.today()))
        session.flush()


# ── 枚举约束 ──────────────────────────────────────────────
def test_question_type_stored_as_value(session):
    u = _mk_user(session)
    wb = _mk_workbook(session, u)
    q = _mk_question(session, wb, type_=QuestionType.fill_blank, answer="42")
    session.flush()
    session.expire_all()
    got = session.get(Question, q.id)
    assert got.type == QuestionType.fill_blank
    assert got.type.value == "fill_blank"
