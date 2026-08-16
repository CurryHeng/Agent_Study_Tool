"""会话业务逻辑（#46/#47）。"""
from sqlalchemy.orm import Session

from models import ConversationMessage, User
from repositories import conversation_repository
from schemas.conversation import ConversationMessageOut, ConversationOut
from services import access


def _get_owned(db: Session, user: User, conversation_id: int):
    conv = conversation_repository.get_by_id(db, conversation_id)
    if conv is None or conv.user_id != user.id:
        raise access.AccessError(404, "会话不存在")
    return conv


def list_conversations(db: Session, user: User) -> list[ConversationOut]:
    conversations = conversation_repository.list_by_user(db, user.id)
    result: list[ConversationOut] = []
    for conv in conversations:
        messages = conversation_repository.list_messages(
            db, conv.id, limit=1, offset=0
        )
        last_message = messages[-1].content if messages else None
        result.append(
            ConversationOut(
                id=conv.id,
                title=conv.title,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                last_message=last_message,
            )
        )
    return result


def create_conversation(db: Session, user: User, title: str | None = None) -> ConversationOut:
    conv = conversation_repository.create(db, user.id, title)
    return ConversationOut(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        last_message=None,
    )


def get_messages(
    db: Session,
    user: User,
    conversation_id: int,
    limit: int = 50,
    offset: int = 0,
) -> list[ConversationMessageOut]:
    _get_owned(db, user, conversation_id)
    messages: list[ConversationMessage] = conversation_repository.list_messages(
        db, conversation_id, limit=limit, offset=offset
    )
    return [
        ConversationMessageOut(
            id=m.id,
            conversation_id=m.conversation_id,
            role=m.role,
            content=m.content,
            metadata=m.payload,
            created_at=m.created_at,
        )
        for m in messages
    ]


def delete_conversation(db: Session, user: User, conversation_id: int) -> None:
    conv = _get_owned(db, user, conversation_id)
    conversation_repository.delete(db, conv)
