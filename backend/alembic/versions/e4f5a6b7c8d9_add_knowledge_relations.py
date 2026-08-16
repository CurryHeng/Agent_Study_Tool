"""add knowledge_relations

Revision ID: e4f5a6b7c8d9
Revises: d2e3f4a5b6c7
Create Date: 2026-08-16
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e4f5a6b7c8d9"
down_revision: str | Sequence[str] | None = "d2e3f4a5b6c7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_relations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("workbook_id", sa.Integer(), nullable=False, index=True),
        sa.Column("source_knowledge_id", sa.Integer(), nullable=False, index=True),
        sa.Column("target_knowledge_id", sa.Integer(), nullable=False, index=True),
        sa.Column("relation_type", sa.String(length=32), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["workbook_id"], ["workbooks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_knowledge_id"], ["knowledge.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_knowledge_id"], ["knowledge.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("knowledge_relations")
