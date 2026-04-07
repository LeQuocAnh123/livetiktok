"""add sentiment to message_logs

Revision ID: 5609818da4ea
Revises: 1a45e7a2e4c8
Create Date: 2026-04-08 01:02:33.854506

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5609818da4ea"
down_revision: Union[str, Sequence[str], None] = "1a45e7a2e4c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "message_logs",
        sa.Column("sentiment", sa.String(), nullable=False, server_default="neutral"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("message_logs", "sentiment")
