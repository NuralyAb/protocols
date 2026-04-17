from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class LiveSessionCreate(BaseModel):
    title: str | None = None
    languages: list[str] = Field(default_factory=lambda: ["kk", "ru", "en"])
    asr_provider: Literal[
        "openai", "openai_transcribe", "local", "local_kazakh", "hf_kazakh", "hf_space"
    ] = "local"


class LiveSessionOut(BaseModel):
    id: UUID
    title: str | None = None
    is_active: bool
    languages: list[str] | None = None
    asr_provider: str = "local"
    audio_key: str | None = None
    viewer_token: str | None = None
    friendly_id: str | None = None
    started_at: datetime
    ended_at: datetime | None = None

    model_config = {"from_attributes": True}


class ViewerTokenOut(BaseModel):
    session_id: UUID
    viewer_token: str
    public_url_path: str  # frontend should prepend its origin


class PublicSessionOut(BaseModel):
    id: UUID
    title: str | None = None
    is_active: bool
    languages: list[str] | None = None
    started_at: datetime
    ended_at: datetime | None = None


class TemplateOut(BaseModel):
    id: str
    name: str
    description: str
    language: str


class ProtocolGenerateRequest(BaseModel):
    template_id: str
    format: Literal["markdown", "docx", "pdf"] = "markdown"
