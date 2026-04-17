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


_BATCH_INSTRUCT = (
    "You translate numbered transcript lines to {tgt}.\n"
    "Rules:\n"
    "— Return a JSON object: {{\"items\": [<string>, <string>, ...]}} with EXACTLY {n} items, in the same order.\n"
    "— Each item is the translation of the correspondingly-numbered line.\n"
    "— If a source line is already in {tgt}, return it unchanged.\n"
    "— Preserve proper nouns, numbers, dates, IDs verbatim.\n"
    "— Do not merge, split, or re-order lines. Partial sentences stay partial.\n"
    "— No preamble, no quotes, no markdown."
)


def translate_batch(texts: list[str], target: str) -> list[str]:
    """Translate many transcript segments in a single LLM call.

    Returns a list of translations aligned 1:1 with `texts`. Empty strings are
    preserved as empty. Failures fall back to the original text for that slot.
    """
    import json

    tgt = (target or "").lower()
    if tgt not in SUPPORTED:
        raise ValueError(f"Unsupported target language: {target}")
    if not texts:
        return []

    indexed = [(i, (t or "").strip()) for i, t in enumerate(texts)]
    non_empty = [(i, t) for i, t in indexed if t]
    out: list[str] = ["" for _ in texts]
    if not non_empty:
        return out

    settings = get_settings()
    client = _client()

    payload = "\n".join(f"{k}. {t}" for k, (_, t) in enumerate(non_empty, start=1))
    instructions = _BATCH_INSTRUCT.format(tgt=_NAME[tgt], n=len(non_empty))  # type: ignore[index]

    log.info("llm.translate.batch", tgt=tgt, n=len(non_empty))
    resp = client.responses.create(
        model=settings.llm_model,
        instructions=instructions,
        input=[{"role": "user", "content": payload}],
        response_format={"type": "json_object"},  # type: ignore[arg-type]
    )
    raw = (resp.output_text or "").strip()
    try:
        parsed = json.loads(raw)
        items = parsed.get("items") if isinstance(parsed, dict) else None
        if not isinstance(items, list):
            raise ValueError("items missing")
    except Exception as e:  # noqa: BLE001
        log.warning("llm.translate.batch_parse_failed", err=str(e), sample=raw[:200])
        # Fallback: use original text
        for i, t in non_empty:
            out[i] = t
        return out

    for slot, (orig_idx, orig_text) in enumerate(non_empty):
        if slot < len(items) and isinstance(items[slot], str) and items[slot].strip():
            out[orig_idx] = items[slot].strip()
        else:
            out[orig_idx] = orig_text
    return out


__all__ = ["translate", "translate_batch", "SUPPORTED"]
