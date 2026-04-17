"""Add translations JSONB to transcript_segments

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-17
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("transcript_segments") as batch:
        batch.add_column(sa.Column("translations", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("transcript_segments") as batch:
        batch.drop_column("translations")
