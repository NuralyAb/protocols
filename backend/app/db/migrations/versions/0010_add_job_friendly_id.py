"""Add friendly_id (DDMMYYYY-HHMM) to jobs for Telegram bot lookups

Revision ID: 0010
Revises: 0009
Create Date: 2026-04-17
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("jobs") as batch:
        batch.add_column(sa.Column("friendly_id", sa.String(32), nullable=True))
    op.create_index(
        "ix_jobs_friendly_id",
        "jobs",
        ["friendly_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_jobs_friendly_id", table_name="jobs")
    with op.batch_alter_table("jobs") as batch:
        batch.drop_column("friendly_id")
