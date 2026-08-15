"""SM-2 -> FSRS-6: review_cards 调度字段迁移

Revision ID: a1b2c3d4e5f6
Revises: 55497f64d4b9
Create Date: 2026-08-15

review_cards 字段变更：
- 废弃 ease / interval / repetitions / next_review(Date)
- 新增 state / step / stability / difficulty / due(DateTime, naive UTC)
- last_review Date -> DateTime

存量数据转换策略（近似即可，量小）：
- repetitions > 0 -> state='Review'，否则 'Learning'
- stability <- max(interval, 1)（SM-2 间隔天数近似记忆稳定度）
- difficulty <- 5.0（FSRS 默认中值）
- due <- next_review 当日 00:00 UTC
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "55497f64d4b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("review_cards") as batch:
        batch.add_column(sa.Column("state", sa.String(16), nullable=False, server_default="Learning"))
        batch.add_column(sa.Column("step", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("stability", sa.Float(), nullable=True))
        batch.add_column(sa.Column("difficulty", sa.Float(), nullable=True))
        batch.add_column(sa.Column("due", sa.DateTime(), nullable=True))
        batch.alter_column("last_review", type_=sa.DateTime(), existing_type=sa.Date())

    # 存量数据近似转换
    op.execute(
        """
        UPDATE review_cards SET
            state = CASE WHEN repetitions > 0 THEN 'Review' ELSE 'Learning' END,
            stability = MAX(COALESCE(interval, 1), 1),
            difficulty = 5.0,
            due = datetime(next_review)
        """
    )

    with op.batch_alter_table("review_cards") as batch:
        batch.alter_column("due", existing_type=sa.DateTime(), nullable=False)
        batch.drop_column("ease")
        batch.drop_column("interval")
        batch.drop_column("repetitions")
        batch.drop_column("next_review")
        batch.drop_index("ix_review_cards_user_next")
        batch.create_index("ix_review_cards_user_due", ["user_id", "due"])


def downgrade() -> None:
    with op.batch_alter_table("review_cards") as batch:
        batch.add_column(sa.Column("ease", sa.Float(), nullable=False, server_default="2.5"))
        batch.add_column(sa.Column("interval", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("repetitions", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("next_review", sa.Date(), nullable=True))
        batch.alter_column("last_review", type_=sa.Date(), existing_type=sa.DateTime())

    op.execute("UPDATE review_cards SET next_review = date(due)")

    with op.batch_alter_table("review_cards") as batch:
        batch.alter_column("next_review", existing_type=sa.Date(), nullable=False)
        batch.drop_column("state")
        batch.drop_column("step")
        batch.drop_column("stability")
        batch.drop_column("difficulty")
        batch.drop_column("due")
        batch.drop_index("ix_review_cards_user_due")
        batch.create_index("ix_review_cards_user_next", ["user_id", "next_review"])
