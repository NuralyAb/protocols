from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.db.models import InputModality, JobStatus


class JobCreateResponse(BaseModel):
    job_id: UUID
    status: JobStatus


class JobStatusOut(BaseModel):
    id: UUID
    status: JobStatus
    progress: int
    error: str | None = None


class TranscriptSegmentOut(BaseModel):
    speaker: str
    role: str | None = None
    language: str | None = None
    input_modality: InputModality = InputModality.speech
    start_time: int  # ms
    end_time: int  # ms
    text: str
    confidence: float | None = None


class JobOut(BaseModel):
    id: UUID
    title: str | None = None
    status: JobStatus
    progress: int
    source_filename: str | None = None
    duration_ms: int | None = None
    languages_detected: list[str] | None = None
    result: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SpeakerPatch(BaseModel):
    diarization_id: str
    label: str | None = None
    role: str | None = None
