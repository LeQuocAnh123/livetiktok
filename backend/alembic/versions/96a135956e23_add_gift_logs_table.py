"""add gift_logs table

Revision ID: 96a135956e23
Revises: 5609818da4ea
Create Date: 2026-04-08 01:57:32.937417

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "96a135956e23"
down_revision: Union[str, Sequence[str], None] = "5609818da4ea"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "gift_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("user_unique_id", sa.String(), nullable=False),
        sa.Column("gift_name", sa.String(), nullable=False),
        sa.Column("diamond_count", sa.Integer(), nullable=False),
        sa.Column("repeat_count", sa.Integer(), nullable=False),
        sa.Column("total_diamonds", sa.Integer(), nullable=False),
        sa.Column("estimated_usd", sa.Float(), nullable=False),
        sa.Column("thank_reply", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["live_sessions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_gift_dedup",
        "gift_logs",
        ["session_id", "user_unique_id", "gift_name", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_gift_dedup", table_name="gift_logs")
    op.drop_table("gift_logs")
