"""Add asr_provider column to live_sessions

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-16
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("live_sessions") as batch:
        batch.add_column(
            sa.Column("asr_provider", sa.String(16), nullable=False, server_default="local")
        )


def downgrade() -> None:
    with op.batch_alter_table("live_sessions") as batch:
        batch.drop_column("asr_provider")
