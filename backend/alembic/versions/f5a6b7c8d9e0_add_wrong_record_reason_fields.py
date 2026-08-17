"""add wrong_records reason fields

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-08-16

wrong_records 新增错因分析三列（P1-1 契约 3）：
- reason_type: 错因类型枚举（概念不清/记忆遗忘/审题偏差/计算失误/方法不当/其他）
- ai_explanation: LLM 归因解释
- ai_suggestion: 改进建议
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f5a6b7c8d9e0"
down_revision: str | Sequence[str] | None = "e4f5a6b7c8d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("wrong_records") as batch:
        batch.add_column(sa.Column("reason_type", sa.String(length=32), nullable=True))
        batch.add_column(sa.Column("ai_explanation", sa.Text(), nullable=True))
        batch.add_column(sa.Column("ai_suggestion", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("wrong_records") as batch:
        batch.drop_column("reason_type")
        batch.drop_column("ai_explanation")
        batch.drop_column("ai_suggestion")
