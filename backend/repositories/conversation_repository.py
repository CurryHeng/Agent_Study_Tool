"""会话与消息数据访问层。"""
from sqlalchemy.orm import Session

from models import Conversation, ConversationMessage


def list_by_user(db: Session, user_id: int) -> list[Conversation]:
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )


def get_by_id(db: Session, conversation_id: int) -> Conversation | None:
    return db.get(Conversation, conversation_id)


def create(db: Session, user_id: int, title: str | None = None) -> Conversation:
    conv = Conversation(user_id=user_id, title=title)
    db.add(conv)
    db.flush()
    return conv


def delete(db: Session, conversation: Conversation) -> None:
    db.delete(conversation)
    db.flush()


def add_message(
    db: Session,
    conversation_id: int,
    role: str,
    content: str,
    metadata: dict | None = None,
) -> ConversationMessage:
    msg = ConversationMessage(
        conversation_id=conversation_id,
        role=role,
        content=content,
        payload=metadata,
    )
    db.add(msg)
    db.flush()
    # 更新会话 updated_at
    conv = db.get(Conversation, conversation_id)
    if conv is not None:
        conv.updated_at = conv.updated_at  # onupdate 会在 flush 时自动更新
    return msg


def list_messages(
    db: Session, conversation_id: int, limit: int = 50, offset: int = 0
) -> list[ConversationMessage]:
    return (
        db.query(ConversationMessage)
        .filter(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.created_at.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
