"""Add viewer_token column to live_sessions for read-only public access

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-17
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("live_sessions") as batch:
        batch.add_column(sa.Column("viewer_token", sa.String(64), nullable=True))
    op.create_index(
        "ix_live_sessions_viewer_token",
        "live_sessions",
        ["viewer_token"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_live_sessions_viewer_token", table_name="live_sessions")
    with op.batch_alter_table("live_sessions") as batch:
        batch.drop_column("viewer_token")
