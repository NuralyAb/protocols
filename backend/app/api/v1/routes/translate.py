"""Translation endpoint for transcript segments (kk/ru/en)."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.v1.deps import CurrentUser
from app.services.summarization.translator import SUPPORTED, translate

router = APIRouter()

_MAX_CHARS = 4000


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=_MAX_CHARS)
    source: str | None = Field(default=None, description="Source lang (kk/ru/en) or null to auto-detect")
    target: str = Field(..., description="Target lang (kk/ru/en)")


class TranslateResponse(BaseModel):
    text: str
    source: str | None
    target: str


@router.post("/translate", response_model=TranslateResponse)
async def translate_text(body: TranslateRequest, user: CurrentUser) -> TranslateResponse:
    _ = user  # auth-gated
    tgt = body.target.lower()
    src = (body.source or "").lower() or None
    if tgt not in SUPPORTED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unsupported target language: {body.target}")
    if src and src not in SUPPORTED:
        # Treat unknown source as auto-detect rather than rejecting outright.
        src = None
    try:
        translated = await asyncio.to_thread(translate, body.text, src or "", tgt)
    except RuntimeError as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e)) from e
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Translation failed: {e}") from e
    return TranslateResponse(text=translated, source=src, target=tgt)
