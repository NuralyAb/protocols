"""LLM summarization service.

- Uses OpenAI's Python SDK with ``responses.parse`` to constrain outputs to our Pydantic schemas.
- Automatically chunks long transcripts (map step) and reduces partials into one protocol.
- Language of the output follows the dominant detected language (kk/ru/en).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.summarization.prompts import (
    MAP_INSTRUCTIONS,
    REDUCE_INSTRUCTIONS,
    SYSTEM,
    Lang,
    pick_language,
)
from app.services.summarization.schemas import (
    ActionItem,
    ChunkSummary,
    Decision,
    DiscussionTopic,
    ProtocolDraft,
)

if TYPE_CHECKING:
    from openai import OpenAI

log = get_logger("llm.summarizer")


# Rough char budget per chunk — cheap proxy for tokens, works well for kk/ru/en mix.
# ~4 chars/token → 12k chars ≈ 3k tokens, leaving headroom for prompt + output.
MAX_CHARS_PER_CHUNK = 12_000


def _client() -> "OpenAI":
    from openai import OpenAI

    s = get_settings()
    if not s.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    return OpenAI(api_key=s.openai_api_key)


def _format_transcript(transcript: list[dict[str, Any]]) -> str:
    """Serialize transcript segments into a compact, LLM-friendly form."""
    lines: list[str] = []
    for seg in transcript:
        t = int(seg.get("start_time", 0)) // 1000
        mm, ss = divmod(t, 60)
        speaker = seg.get("speaker") or "SPEAKER_?"
        lang = seg.get("language") or "?"
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        lines.append(f"[{mm:02d}:{ss:02d}] ({lang}) {speaker}: {text}")
    return "\n".join(lines)


def _chunk(lines: str, max_chars: int = MAX_CHARS_PER_CHUNK) -> list[str]:
    if len(lines) <= max_chars:
        return [lines]
    chunks: list[str] = []
    buf: list[str] = []
    size = 0
    for line in lines.splitlines(keepends=True):
        if size + len(line) > max_chars and buf:
            chunks.append("".join(buf))
            buf, size = [], 0
        buf.append(line)
        size += len(line)
    if buf:
        chunks.append("".join(buf))
    return chunks


def _map(client: "OpenAI", model: str, lang: Lang, chunk_text: str, idx: int, total: int) -> ChunkSummary:
    log.info("llm.map", chunk=idx + 1, total=total, chars=len(chunk_text))
    resp = client.responses.parse(
        model=model,
        instructions=f"{SYSTEM[lang]}\n\n{MAP_INSTRUCTIONS[lang]}",
        input=[
            {
                "role": "user",
                "content": (
                    f"Фрагмент {idx + 1}/{total}.\n\n"
                    f"Transcript:\n{chunk_text}"
                ),
            }
        ],
        text_format=ChunkSummary,
    )
    return resp.output_parsed or ChunkSummary(summary="")


def _reduce(
    client: "OpenAI",
    model: str,
    lang: Lang,
    partials: list[ChunkSummary],
    full_transcript_excerpt: str,
) -> ProtocolDraft:
    log.info("llm.reduce", partials=len(partials))
    partials_json = [p.model_dump(by_alias=True) for p in partials]
    user_msg = (
        f"Partial summaries (JSON array):\n{partials_json}\n\n"
        f"Short transcript excerpt for grounding:\n{full_transcript_excerpt[:4000]}"
    )
    resp = client.responses.parse(
        model=model,
        instructions=f"{SYSTEM[lang]}\n\n{REDUCE_INSTRUCTIONS[lang]}",
        input=[{"role": "user", "content": user_msg}],
        text_format=ProtocolDraft,
    )
    return resp.output_parsed or ProtocolDraft()


def summarize(
    transcript: list[dict[str, Any]],
    languages_detected: list[str] | None = None,
) -> ProtocolDraft:
    """Main entrypoint. Returns a ProtocolDraft you can merge into Job.result.protocol."""
    if not transcript:
        return ProtocolDraft()

    settings = get_settings()
    model = settings.llm_model
    lang: Lang = pick_language(languages_detected)

    serialized = _format_transcript(transcript)
    chunks = _chunk(serialized)
    client = _client()

    # Single-chunk fast path — skip map/reduce roundtrip.
    if len(chunks) == 1:
        log.info("llm.single_pass", chars=len(serialized), lang=lang)
        resp = client.responses.parse(
            model=model,
            instructions=f"{SYSTEM[lang]}\n\n{REDUCE_INSTRUCTIONS[lang]}",
            input=[
                {
                    "role": "user",
                    "content": f"Transcript:\n{serialized}",
                }
            ],
            text_format=ProtocolDraft,
        )
        return resp.output_parsed or ProtocolDraft()

    partials: list[ChunkSummary] = []
    for i, ch in enumerate(chunks):
        partials.append(_map(client, model, lang, ch, i, len(chunks)))

    return _reduce(client, model, lang, partials, serialized)


def merge_into_result(result: dict[str, Any], draft: ProtocolDraft) -> dict[str, Any]:
    """Merge a ProtocolDraft into the pipeline result dict (in place)."""
    proto = result.setdefault("protocol", {})
    proto["title"] = draft.title or proto.get("title")
    proto["date"] = draft.date or proto.get("date")
    proto["agenda"] = draft.agenda
    proto["discussion"] = [d.model_dump() for d in draft.discussion]
    proto["decisions"] = [d.model_dump(by_alias=True) for d in draft.decisions]
    proto["action_items"] = [a.model_dump() for a in draft.action_items]
    result.setdefault("metadata", {}).setdefault("model_versions", {})["summarizer"] = (
        get_settings().llm_model
    )
    return result


__all__ = [
    "ProtocolDraft",
    "ChunkSummary",
    "Decision",
    "ActionItem",
    "DiscussionTopic",
    "summarize",
    "merge_into_result",
]
