"""业务枚举定义。

成员名与值保持一致（小写），这样 SQLAlchemy 的 Enum 列默认按成员名存储，
落库值即为期望的字符串，读取时返回枚举成员。
"""
from enum import StrEnum


class QuestionType(StrEnum):
    single_choice = "single_choice"
    multiple_choice = "multiple_choice"
    true_false = "true_false"
    fill_blank = "fill_blank"
    short_answer = "short_answer"


class QuestionSource(StrEnum):
    builtin = "builtin"        # 系统内置参考题
    imported = "imported"      # 用户导入
    ai = "ai"                  # AI 生成
    user = "user"              # 用户手动创建


class QuestionStatus(StrEnum):
    generated = "generated"    # AI 刚生成
    reviewing = "reviewing"    # 审核中
    approved = "approved"      # 通过，可进入正式题库
    rejected = "rejected"      # 审核不通过


class DocumentStatus(StrEnum):
    pending = "pending"
    processing = "processing"
    success = "success"
    failed = "failed"


class AgentTaskStatus(StrEnum):
    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"
    cancelled = "cancelled"


# 选择题型集合（单选/多选/判断），供判题、出题校验、题库校验复用
CHOICE_TYPES = frozenset(
    {QuestionType.single_choice, QuestionType.multiple_choice, QuestionType.true_false}
)
