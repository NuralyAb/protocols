from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class LiveSessionCreate(BaseModel):
    title: str | None = None
    languages: list[str] = Field(default_factory=lambda: ["kk", "ru", "en"])
    asr_provider: Literal["openai", "local", "local_kazakh", "hf_kazakh"] = "local"


class LiveSessionOut(BaseModel):
    id: UUID
    title: str | None = None
    is_active: bool
    languages: list[str] | None = None
    asr_provider: str = "local"
    started_at: datetime
    ended_at: datetime | None = None

    model_config = {"from_attributes": True}


class TemplateOut(BaseModel):
    id: str
    name: str
    description: str
    language: str


class ProtocolGenerateRequest(BaseModel):
    template_id: str
    format: Literal["markdown", "docx", "pdf"] = "markdown"
