"""remove sign-language related columns

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-15
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("speakers") as batch:
        batch.drop_column("hearing_impaired")
        batch.drop_column("sign_language")
    with op.batch_alter_table("live_sessions") as batch:
        batch.drop_column("sign_language_enabled")
        batch.drop_column("sign_language")


def downgrade() -> None:
    with op.batch_alter_table("live_sessions") as batch:
        batch.add_column(sa.Column("sign_language", sa.String(16)))
        batch.add_column(
            sa.Column("sign_language_enabled", sa.Boolean, nullable=False, server_default=sa.false())
        )
    with op.batch_alter_table("speakers") as batch:
        batch.add_column(sa.Column("sign_language", sa.String(16)))
        batch.add_column(
            sa.Column("hearing_impaired", sa.Boolean, nullable=False, server_default=sa.false())
        )
