"""Add audio_key column to live_sessions

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-17
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("live_sessions") as batch:
        batch.add_column(sa.Column("audio_key", sa.String(500), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("live_sessions") as batch:
        batch.drop_column("audio_key")
