"""Vector-based question-answering over a session transcript.

Tiny RAG: chunk the transcript by speaker turns, embed each chunk with the
OpenAI embeddings API, retrieve top-K by cosine similarity, then ask GPT-4o
to answer in the requested language using only the retrieved context.

Embeddings are cached in-process per (session_id, transcript_hash). The cache
is best-effort and rebuilt when the transcript grows.
"""
from __future__ import annotations

import hashlib
import math
from typing import Any, Literal

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger("qa")

Lang = Literal["kk", "ru", "en"]

EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_K = 6
MAX_CHARS_PER_CHUNK = 700
EMBED_BATCH = 96


_SYSTEM: dict[Lang, str] = {
    "ru": (
        "Ты — ассистент, отвечающий на вопросы по транскрипту заседания. "
        "Используй только приведённые ниже фрагменты транскрипта. Если ответа в них нет — так и скажи. "
        "Ссылайся на тайм-коды формата [MM:SS] из контекста, когда это уместно. "
        "Отвечай по существу, без воды; язык ответа — русский."
    ),
    "kk": (
        "Сен — жиналыс транскриптіне сүйеніп жауап беретін көмекшісің. "
        "Тек төмендегі үзінділерді пайдалан. Жауап табылмаса — ашық айт. "
        "Орынды болса, [MM:SS] тайм-кодтарына сілтеме бер. "
        "Қысқа және нақты жауап бер, тек қазақ тілінде."
    ),
    "en": (
        "You answer questions about a meeting transcript. "
        "Use only the snippets provided below. If the answer is not present, say so plainly. "
        "Reference [MM:SS] timecodes from the context when appropriate. "
        "Be concise and direct. Answer in English."
    ),
}


def _client():
    from openai import OpenAI

    s = get_settings()
    if not s.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    return OpenAI(api_key=s.openai_api_key)


def _mmss(ms: int) -> str:
    s = max(0, ms // 1000)
    return f"{s // 60:02d}:{s % 60:02d}"


def _hash_transcript(transcript: list[dict[str, Any]]) -> str:
    h = hashlib.sha1()
    for seg in transcript:
        h.update(str(seg.get("start_time", 0)).encode())
        h.update(b"|")
        h.update(str(seg.get("speaker") or "").encode())
        h.update(b"|")
        h.update((seg.get("text") or "").encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()[:16]


def _chunk_transcript(transcript: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group consecutive segments by speaker; split if a chunk grows too long."""
    chunks: list[dict[str, Any]] = []
    cur: dict[str, Any] | None = None
    for seg in transcript:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        sp = seg.get("speaker") or "SPEAKER_?"
        if (
            cur is not None
            and cur["speaker"] == sp
            and len(cur["text"]) + len(text) + 1 <= MAX_CHARS_PER_CHUNK
        ):
            cur["text"] += "\n" + text
            cur["end_ms"] = int(seg.get("end_time") or cur["end_ms"])
        else:
            if cur is not None:
                chunks.append(cur)
            cur = {
                "speaker": sp,
                "start_ms": int(seg.get("start_time") or 0),
                "end_ms": int(seg.get("end_time") or 0),
                "text": text,
            }
    if cur is not None:
        chunks.append(cur)
    return chunks


def _embed_many(texts: list[str]) -> list[list[float]]:
    client = _client()
    out: list[list[float]] = []
    for i in range(0, len(texts), EMBED_BATCH):
        batch = texts[i : i + EMBED_BATCH]
        resp = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        out.extend(d.embedding for d in resp.data)
    return out


def _cosine(a: list[float], b: list[float]) -> float:
    s = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return s / (na * nb) if na and nb else 0.0


# In-process cache: {session_id: {"hash": str, "chunks": [...], "vectors": [[...]]}}
_INDEX: dict[str, dict[str, Any]] = {}


def index_for(session_id: str, transcript: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return (or build) the chunk + vector index for a session."""
    if not transcript:
        _INDEX.pop(session_id, None)
        return None
    h = _hash_transcript(transcript)
    cached = _INDEX.get(session_id)
    if cached and cached.get("hash") == h:
        return cached
    chunks = _chunk_transcript(transcript)
    if not chunks:
        return None
    vectors = _embed_many([c["text"] for c in chunks])
    entry = {"hash": h, "chunks": chunks, "vectors": vectors}
    _INDEX[session_id] = entry
    log.info("qa.index_built", sid=session_id, chunks=len(chunks))
    return entry


def retrieve(
    session_id: str,
    transcript: list[dict[str, Any]],
    query: str,
    *,
    k: int = DEFAULT_K,
) -> list[dict[str, Any]]:
    entry = index_for(session_id, transcript)
    if not entry:
        return []
    q_vec = _embed_many([query])[0]
    scored = [
        (_cosine(q_vec, vec), chunk) for vec, chunk in zip(entry["vectors"], entry["chunks"])
    ]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {**c, "score": round(s, 4)} for s, c in scored[:k] if s > 0.05
    ]


def _format_context(snippets: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for sn in snippets:
        lines.append(f"[{_mmss(sn['start_ms'])}–{_mmss(sn['end_ms'])}] {sn['speaker']}: {sn['text']}")
    return "\n\n".join(lines)


def pick_lang(hint: str | None, languages_detected: list[str] | None) -> Lang:
    if hint and hint in ("kk", "ru", "en"):
        return hint  # type: ignore[return-value]
    if languages_detected:
        first = languages_detected[0]
        if first in ("kk", "ru", "en"):
            return first  # type: ignore[return-value]
    return "ru"


def answer(
    session_id: str,
    transcript: list[dict[str, Any]],
    question: str,
    *,
    lang: Lang = "ru",
    k: int = DEFAULT_K,
) -> dict[str, Any]:
    """Run the full RAG pipeline: retrieve top-K chunks, ask GPT-4o, return answer + sources."""
    settings = get_settings()
    snippets = retrieve(session_id, transcript, question, k=k)
    if not snippets:
        no_data = {
            "ru": "В транскрипте пока нет данных по этому вопросу.",
            "kk": "Транскриптте бұл сұрақ бойынша дерек жоқ.",
            "en": "There is no relevant content in the transcript yet.",
        }
        return {"answer": no_data[lang], "sources": []}

    context = _format_context(snippets)
    user_msg = f"# КОНТЕКСТ / CONTEXT\n\n{context}\n\n# ВОПРОС / QUESTION\n\n{question}"

    client = _client()
    log.info("qa.answer", sid=session_id, snippets=len(snippets), lang=lang)
    resp = client.responses.create(
        model=settings.llm_model,
        instructions=_SYSTEM[lang],
        input=[{"role": "user", "content": user_msg}],
    )
    text = (resp.output_text or "").strip()
    return {
        "answer": text,
        "sources": [
            {"start_ms": s["start_ms"], "end_ms": s["end_ms"], "speaker": s["speaker"], "score": s["score"]}
            for s in snippets
        ],
    }


__all__ = ["answer", "index_for", "retrieve", "pick_lang", "Lang"]
