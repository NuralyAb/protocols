"""Structured-output schemas for meeting protocol summarization.

These models are handed to OpenAI via `responses.parse(...)` so the model is
constrained to fill exactly this shape — no ad-hoc JSON parsing.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class VoteCount(BaseModel):
    for_: int = Field(0, alias="for", ge=0)
    against: int = Field(0, ge=0)
    abstain: int = Field(0, ge=0)

    model_config = {"populate_by_name": True}


class Decision(BaseModel):
    text: str
    votes: VoteCount | None = None
    speakers: list[str] = Field(default_factory=list)


class ActionItem(BaseModel):
    task: str
    assignee: str | None = None
    deadline: str | None = None  # free-form: "до 1 мая", "2026-05-01", etc.


class DiscussionTopic(BaseModel):
    topic: str
    summary: str
    speakers: list[str] = Field(default_factory=list)


class ProtocolDraft(BaseModel):
    title: str | None = None
    date: str | None = None
    agenda: list[str] = Field(default_factory=list)
    discussion: list[DiscussionTopic] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)


class ChunkSummary(BaseModel):
    """Intermediate map-step output for long transcripts."""
    summary: str
    speakers: list[str] = Field(default_factory=list)
    facts: list[str] = Field(default_factory=list)
    candidate_decisions: list[Decision] = Field(default_factory=list)
    candidate_actions: list[ActionItem] = Field(default_factory=list)
