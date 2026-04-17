"""Add friendly_id (DDMMYYYY-HHMM) to live_sessions for Telegram bot lookups

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-17
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("live_sessions") as batch:
        batch.add_column(sa.Column("friendly_id", sa.String(32), nullable=True))
    op.create_index(
        "ix_live_sessions_friendly_id",
        "live_sessions",
        ["friendly_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_live_sessions_friendly_id", table_name="live_sessions")
    with op.batch_alter_table("live_sessions") as batch:
        batch.drop_column("friendly_id")
