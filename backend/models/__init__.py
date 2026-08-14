"""汇总导入所有模型，确保 Base.metadata 完整（供 Alembic autogenerate 识别）。"""
from models.agent_task import AgentTask
from models.answer_record import AnswerRecord
from models.api_key import ApiKey
from models.document import Document
from models.knowledge import Knowledge
from models.question import Question
from models.question_option import QuestionOption
from models.refresh_token import RefreshToken
from models.review_card import ReviewCard
from models.user import User
from models.workbook import Workbook
from models.wrong_record import WrongRecord

__all__ = [
    "AgentTask",
    "AnswerRecord",
    "ApiKey",
    "Document",
    "Knowledge",
    "Question",
    "QuestionOption",
    "RefreshToken",
    "ReviewCard",
    "User",
    "Workbook",
    "WrongRecord",
]
