from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class JobStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class InputModality(str, enum.Enum):
    speech = "speech"
    sign = "sign"


class ExportFormat(str, enum.Enum):
    pdf = "pdf"
    docx = "docx"
    json = "json"
    txt = "txt"
    srt = "srt"
    vtt = "vtt"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _uuid_pk()
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    jobs: Mapped[list[Job]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    sessions: Mapped[list[LiveSession]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = _uuid_pk()
    owner_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.pending)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)

    source_key: Mapped[str | None] = mapped_column(String(500))  # S3 key of original audio
    source_filename: Mapped[str | None] = mapped_column(String(500))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    languages_hint: Mapped[list[str] | None] = mapped_column(JSON)

    result: Mapped[dict | None] = mapped_column(JSON)  # full protocol JSON snapshot
    model_versions: Mapped[dict | None] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped[User] = relationship(back_populates="jobs")
    speakers: Mapped[list[Speaker]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    transcript_segments: Mapped[list[TranscriptSegment]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    exports: Mapped[list[Export]] = relationship(back_populates="job", cascade="all, delete-orphan")


class Speaker(Base):
    __tablename__ = "speakers"

    id: Mapped[uuid.UUID] = _uuid_pk()
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), index=True, nullable=True
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("live_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    diarization_id: Mapped[str] = mapped_column(String(64))  # e.g. SPEAKER_00
    label: Mapped[str] = mapped_column(String(255))
    role: Mapped[str | None] = mapped_column(String(128))

    job: Mapped[Job | None] = relationship(back_populates="speakers")
    session: Mapped[LiveSession | None] = relationship(back_populates="speakers")


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[uuid.UUID] = _uuid_pk()
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), index=True, nullable=True
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("live_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    speaker_diarization_id: Mapped[str | None] = mapped_column(String(64))
    language: Mapped[str | None] = mapped_column(String(8))
    input_modality: Mapped[InputModality] = mapped_column(
        Enum(InputModality), default=InputModality.speech
    )
    start_ms: Mapped[int] = mapped_column(Integer)
    end_ms: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job: Mapped[Job | None] = relationship(back_populates="transcript_segments")
    session: Mapped[LiveSession | None] = relationship(back_populates="transcript_segments")


class LiveSession(Base):
    __tablename__ = "live_sessions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    owner_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    languages: Mapped[list[str] | None] = mapped_column(JSON)
    asr_provider: Mapped[str] = mapped_column(String(16), default="local")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    owner: Mapped[User] = relationship(back_populates="sessions")
    speakers: Mapped[list[Speaker]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    transcript_segments: Mapped[list[TranscriptSegment]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class Export(Base):
    __tablename__ = "exports"

    id: Mapped[uuid.UUID] = _uuid_pk()
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), index=True, nullable=True
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("live_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    format: Mapped[ExportFormat] = mapped_column(Enum(ExportFormat))
    s3_key: Mapped[str] = mapped_column(String(500))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job: Mapped[Job | None] = relationship(back_populates="exports")
