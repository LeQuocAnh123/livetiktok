"""add_seller_auth_fields

Revision ID: 1a45e7a2e4c8
Revises: 5b83f14952d2
Create Date: 2026-04-07 23:50:00.549610

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1a45e7a2e4c8"
down_revision: Union[str, Sequence[str], None] = "5b83f14952d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add columns without constraints first (SQLite compatible)
    op.add_column("sellers", sa.Column("username", sa.String(), nullable=True))
    op.add_column("sellers", sa.Column("password_hash", sa.String(), nullable=True))
    op.add_column(
        "sellers", sa.Column("is_active", sa.Boolean(), server_default="1", nullable=True)
    )

    # Create unique index for username lookup
    op.create_index("ix_sellers_username", "sellers", ["username"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_sellers_username", table_name="sellers")
    op.drop_column("sellers", "is_active")
    op.drop_column("sellers", "password_hash")
    op.drop_column("sellers", "username")
