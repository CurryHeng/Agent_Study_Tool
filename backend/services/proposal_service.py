"""Agent 写操作提案：短期保存、用户隔离与确认执行。"""
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from models import User
from schemas.generation import GeneratedQuestion
from schemas.knowledge import KnowledgeCreate, KnowledgeOut, KnowledgeUpdate
from services import access, generation_service, knowledge_service

PROPOSAL_TTL_SEC = 600


@dataclass
class _StoredProposal:
    proposal_id: str
    user_id: int
    action: str
    target: dict[str, Any]
    changes: dict[str, Any]
    impact: str
    payload: dict[str, Any]
    expires_at: datetime


_proposals: dict[str, _StoredProposal] = {}
_lock = Lock()


def create(
    user_id: int,
    action: str,
    target: dict[str, Any],
    changes: dict[str, Any],
    impact: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """保存一个绑定用户的短期提案，并返回前端公开结构。"""
    proposal_id = str(uuid4())
    item = _StoredProposal(
        proposal_id=proposal_id,
        user_id=user_id,
        action=action,
        target=target,
        changes=changes,
        impact=impact,
        payload=payload,
        expires_at=datetime.now(UTC) + timedelta(seconds=PROPOSAL_TTL_SEC),
    )
    with _lock:
        _purge_expired(datetime.now(UTC))
        _proposals[proposal_id] = item
    return _public(item)


def confirm(
    db: Session, user: User, proposal_id: str, approved: bool
) -> dict[str, Any] | None:
    """一次性消费提案；批准时再次鉴权并通过 Service 执行。"""
    with _lock:
        item = _proposals.get(proposal_id)
        now = datetime.now(UTC)
        if item is None or item.user_id != user.id:
            raise access.AccessError(404, "提案不存在")
        del _proposals[proposal_id]
    if item.expires_at <= now:
        raise access.AccessError(410, "提案已过期")
    if not approved:
        return {"approved": False}
    return _execute(db, user, item)


def _execute(db: Session, user: User, item: _StoredProposal) -> dict[str, Any]:
    payload = item.payload
    if item.action == "generate_questions":
        access.get_owned_workbook(db, user, payload["workbook_id"])
        questions = [GeneratedQuestion.model_validate(q) for q in payload["questions"]]
        saved = generation_service.save_questions(
            db, payload["workbook_id"], payload.get("knowledge_id"), questions
        )
        return {"saved": len(saved), "questions": [q.model_dump(mode="json") for q in saved]}
    if item.action == "add_knowledge_node":
        node = knowledge_service.create_knowledge(
            db, user, KnowledgeCreate.model_validate(payload)
        )
        return KnowledgeOut.model_validate(node).model_dump(mode="json")
    knowledge_id = payload["knowledge_id"]
    if item.action == "update_knowledge_node":
        node = knowledge_service.update_knowledge(
            db, user, knowledge_id, KnowledgeUpdate.model_validate(payload["changes"])
        )
        return KnowledgeOut.model_validate(node).model_dump(mode="json")
    if item.action == "delete_knowledge_node":
        knowledge_service.delete_knowledge(db, user, knowledge_id)
        return {"deleted": True, "knowledge_id": knowledge_id}
    raise access.AccessError(422, "不支持的提案动作")


def _public(item: _StoredProposal) -> dict[str, Any]:
    return {
        "proposal_id": item.proposal_id,
        "action": item.action,
        "target": item.target,
        "changes": item.changes,
        "impact": item.impact,
        "expires_in_sec": PROPOSAL_TTL_SEC,
    }


def _purge_expired(now: datetime) -> None:
    expired = [key for key, item in _proposals.items() if item.expires_at <= now]
    for key in expired:
        del _proposals[key]
