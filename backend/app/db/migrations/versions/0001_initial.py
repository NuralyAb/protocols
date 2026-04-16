"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-15
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels = None
depends_on = None


job_status = sa.Enum("pending", "processing", "completed", "failed", name="jobstatus")
input_modality = sa.Enum("speech", "sign", name="inputmodality")
export_format = sa.Enum("pdf", "docx", "json", "txt", "srt", "vtt", name="exportformat")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("is_superuser", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("title", sa.String(500)),
        sa.Column("status", job_status, nullable=False, server_default="pending"),
        sa.Column("progress", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error", sa.Text),
        sa.Column("source_key", sa.String(500)),
        sa.Column("source_filename", sa.String(500)),
        sa.Column("duration_ms", sa.Integer),
        sa.Column("languages_hint", sa.JSON),
        sa.Column("result", sa.JSON),
        sa.Column("model_versions", sa.JSON),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "live_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("title", sa.String(500)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("sign_language_enabled", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("sign_language", sa.String(16)),
        sa.Column("languages", sa.JSON),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "speakers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), index=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("live_sessions.id", ondelete="CASCADE"), index=True),
        sa.Column("diarization_id", sa.String(64), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("role", sa.String(128)),
        sa.Column("hearing_impaired", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("sign_language", sa.String(16)),
    )

    op.create_table(
        "transcript_segments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), index=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("live_sessions.id", ondelete="CASCADE"), index=True),
        sa.Column("speaker_diarization_id", sa.String(64)),
        sa.Column("language", sa.String(8)),
        sa.Column("input_modality", input_modality, nullable=False, server_default="speech"),
        sa.Column("start_ms", sa.Integer, nullable=False),
        sa.Column("end_ms", sa.Integer, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("confidence", sa.Float),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "exports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), index=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("live_sessions.id", ondelete="CASCADE"), index=True),
        sa.Column("format", export_format, nullable=False),
        sa.Column("s3_key", sa.String(500), nullable=False),
        sa.Column("size_bytes", sa.Integer),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("exports")
    op.drop_table("transcript_segments")
    op.drop_table("speakers")
    op.drop_table("live_sessions")
    op.drop_table("jobs")
    op.drop_table("users")
    export_format.drop(op.get_bind(), checkfirst=True)
    input_modality.drop(op.get_bind(), checkfirst=True)
    job_status.drop(op.get_bind(), checkfirst=True)
