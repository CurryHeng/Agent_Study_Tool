"""normalize review_cards malformed datetime values

旧数据中 last_review 存在整数年份（如 2026），导致 SQLAlchemy DateTime
处理器报 TypeError: fromisoformat: argument must be str，统计/刷题接口 500。
此迁移把所有非文本的日期字段置为 NULL（近似清洗，后续写入均为正常 datetime）。
"""
from collections.abc import Sequence

from alembic import op

revision: str = "c1d2e3f4a5b6"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "UPDATE review_cards SET last_review = NULL "
        "WHERE last_review IS NOT NULL AND typeof(last_review) != 'text'"
    )
    op.execute(
        "UPDATE review_cards SET due = NULL "
        "WHERE due IS NOT NULL AND typeof(due) != 'text'"
    )


def downgrade() -> None:
    # 数据清洗不可逆（原始脏值已丢弃）
    pass
