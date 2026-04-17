"""Single-call text translator for transcript segments.

Hands a short text + source/target language pair to OpenAI and expects the
translated text back. Designed for live use — one segment per call, ~50–500
tokens. Caller is responsible for fan-out and caching.
"""
from __future__ import annotations

from typing import Literal

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger("llm.translate")

Lang = Literal["kk", "ru", "en"]
SUPPORTED: tuple[Lang, ...] = ("kk", "ru", "en")

_NAME: dict[Lang, str] = {
    "kk": "Kazakh",
    "ru": "Russian",
    "en": "English",
}

_INSTRUCT = (
    "You are a precise interpreter for live meeting transcripts.\n"
    "Translate the user message from {src} into {tgt}.\n"
    "Rules:\n"
    "— Reply with the translation only. No preamble, no quotes, no explanation.\n"
    "— Preserve speaker tone and meeting register (formal unless source is casual).\n"
    "— Keep proper nouns, numbers, dates and IDs verbatim.\n"
    "— If the source already appears to be {tgt}, return it unchanged.\n"
    "— Never invent missing content; partial sentences stay partial."
)


def _client():
    from openai import OpenAI

    s = get_settings()
    if not s.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    return OpenAI(api_key=s.openai_api_key)


def translate(text: str, source: str, target: str) -> str:
    """Translate a single transcript segment. Raises ValueError on bad lang codes."""
    text = (text or "").strip()
    if not text:
        return ""
    src = source.lower() if source else ""
    tgt = target.lower() if target else ""
    if tgt not in SUPPORTED:
        raise ValueError(f"Unsupported target language: {target}")
    if src not in SUPPORTED:
        # Caller didn't know the language — let the model auto-detect.
        src_name = "the source language (auto-detect)"
    else:
        src_name = _NAME[src]  # type: ignore[index]
    if src == tgt:
        return text

    settings = get_settings()
    client = _client()
    instructions = _INSTRUCT.format(src=src_name, tgt=_NAME[tgt])  # type: ignore[index]

    log.info("llm.translate.call", src=src or "auto", tgt=tgt, chars=len(text))
    resp = client.responses.create(
        model=settings.llm_model,
        instructions=instructions,
        input=[{"role": "user", "content": text}],
    )
    return (resp.output_text or "").strip()


__all__ = ["translate", "SUPPORTED"]
