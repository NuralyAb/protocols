"""Widen asr_provider from VARCHAR(16) to VARCHAR(32) — new provider names longer

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-17
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("live_sessions") as batch:
        batch.alter_column(
            "asr_provider",
            existing_type=sa.String(16),
            type_=sa.String(32),
            existing_nullable=False,
            existing_server_default="local",
        )


def downgrade() -> None:
    with op.batch_alter_table("live_sessions") as batch:
        batch.alter_column(
            "asr_provider",
            existing_type=sa.String(32),
            type_=sa.String(16),
            existing_nullable=False,
            existing_server_default="local",
        )
