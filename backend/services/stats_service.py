"""学习统计聚合服务（只读，聚合当前用户可见范围的数据）。"""
import re
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy.orm import Session

from models import AnswerRecord, Knowledge, Question, ReviewCard, User, WrongRecord
from services import access

_MASTERY_KEYS = ("again", "hard", "good", "easy")

_BUCKETS = [
    ("0-19%", 0, 19),
    ("20-39%", 20, 39),
    ("40-59%", 40, 59),
    ("60-79%", 60, 79),
    ("80-100%", 80, 100),
]

_REASON_PATTERNS = [
    ("计算错误", r"计算|算错|运算|粗心算错"),
    ("概念不清", r"概念|定义|理解偏差|本质"),
    ("公式记错", r"公式|记错|忘记公式|定理|记混"),
    ("看错题", r"看错|看漏|漏看|审题|读题|马虎"),
]


def get_stats(db: Session, user: User) -> dict:
    visible = access.visible_workbook_ids(db, user)
    today = date.today()
    now = datetime.now(UTC)
    monday = datetime.combine(now - timedelta(days=now.weekday()), time.min)

    # ── 复习卡（仅当前用户的卡；题目须在可见工作簿，排除已软删）──
    cards = (
        db.query(ReviewCard)
        .join(Question, Question.id == ReviewCard.question_id)
        .filter(
            ReviewCard.user_id == user.id,
            Question.workbook_id.in_(visible),
            Question.deleted_at.is_(None),
        )
        .all()
    )
    cards_total = len(cards)
    now = datetime.now(UTC).replace(tzinfo=None)
    cards_due = sum(1 for c in cards if c.due <= now)
    reviewed_today = sum(1 for c in cards if c.last_review and c.last_review.date() == today)
    favorites = sum(1 for c in cards if c.favorited)

    # ── 答题记录 ──
    answers = db.query(AnswerRecord).filter(AnswerRecord.user_id == user.id).all()

    mastery: dict[str, int] = {k: 0 for k in _MASTERY_KEYS}
    for a in answers:
        if a.rating in mastery:
            mastery[a.rating] += 1

    # 正确率分布（基于复习卡累计）
    accuracy_buckets = [{"label": b[0], "count": 0} for b in _BUCKETS]
    for c in cards:
        if c.total_attempts <= 0:
            continue
        rate = round(c.total_correct / c.total_attempts * 100)
        for bucket, (_, lo, hi) in zip(accuracy_buckets, _BUCKETS, strict=True):
            if lo <= rate <= hi:
                bucket["count"] += 1
                break

    # 知识点掌握热力图（按答题记录错误率）
    heatmap: dict[str, dict] = {}
    answered_ids = {a.question_id for a in answers}
    if answered_ids:
        rows = (
            db.query(Question.id, Knowledge.name)
            .outerjoin(Knowledge, Knowledge.id == Question.knowledge_id)
            .filter(Question.id.in_(answered_ids))
            .all()
        )
        name_by_qid = {qid: (name or "未分类") for qid, name in rows}
        for a in answers:
            name = name_by_qid.get(a.question_id)
            if name is None:
                continue
            entry = heatmap.setdefault(name, {"total": 0, "errors": 0})
            entry["total"] += 1
            if a.is_correct == 0:
                entry["errors"] += 1
    knowledge_heatmap = sorted(
        ({"name": n, **s} for n, s in heatmap.items() if s["total"] > 0),
        key=lambda x: x["errors"] / x["total"],
        reverse=True,
    )

    # 错因分类
    reasons = db.query(WrongRecord).filter(WrongRecord.user_id == user.id).all()
    reason_count: dict[str, int] = {
        "计算错误": 0,
        "概念不清": 0,
        "公式记错": 0,
        "看错题": 0,
        "其他": 0,
    }
    for w in reasons:
        text = w.wrong_reason or ""
        matched = False
        for name, pattern in _REASON_PATTERNS:
            if re.search(pattern, text):
                reason_count[name] += 1
                matched = True
                break
        if not matched:
            reason_count["其他"] += 1
    wrong_reasons = sorted(
        ({"name": n, "count": c} for n, c in reason_count.items() if c > 0),
        key=lambda x: x["count"],
        reverse=True,
    )

    # 最近答题记录
    recent_answers = sorted(answers, key=lambda a: a.created_at, reverse=True)[:20]
    content_by_qid = {}
    if recent_answers:
        rows = (
            db.query(Question.id, Question.content)
            .filter(Question.id.in_([a.question_id for a in recent_answers]))
            .all()
        )
        content_by_qid = dict(rows)
    recent = [
        {
            "date": a.created_at.date().isoformat(),
            "rating": a.rating,
            "mode": a.mode,
            "is_correct": a.is_correct,
            "question_id": a.question_id,
            "question_content": content_by_qid.get(a.question_id, ""),
        }
        for a in recent_answers
    ]

    # 本周学习时长
    week_answers = [a for a in answers if a.created_at >= monday]
    week_minutes = round(sum((a.time_spent or 0) for a in week_answers) / 60)
    week_days = len({a.created_at.date() for a in week_answers})

    question_total = (
        db.query(Question.id)
        .filter(Question.workbook_id.in_(visible), Question.deleted_at.is_(None))
        .count()
    )

    return {
        "cards_total": cards_total,
        "cards_due": cards_due,
        "reviewed_today": reviewed_today,
        "favorites": favorites,
        "question_total": question_total,
        "mastery": mastery,
        "accuracy_buckets": accuracy_buckets,
        "knowledge_heatmap": knowledge_heatmap,
        "wrong_reasons": wrong_reasons,
        "recent": recent,
        "week_minutes": week_minutes,
        "week_days": week_days,
    }
