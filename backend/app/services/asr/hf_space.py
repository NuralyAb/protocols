"""Client for a user-deployed HuggingFace Space (Gradio).

The Space (default: ``nuraly17/kazakh-asr``) exposes a ``transcribe(audio_path,
language)`` function that returns a JSON string with
``{"text": str, "chunks": [{"timestamp": [start, end], "text": str}, ...]}``.

We treat it like any other ASR backend — the caller hands us a WAV file path
and we return Whisper-compatible segments.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger("asr.hf_space")

DEFAULT_SPACE = os.environ.get("ASR_HF_SPACE", "nuraly17/kazakh-asr")


@dataclass(slots=True)
class HFSegment:
    start_ms: int
    end_ms: int
    text: str
    language: str
    avg_logprob: float
    no_speech_prob: float


def _client(space: str):
    """Lazy import to keep `gradio-client` off the API hot path."""
    from gradio_client import Client

    s = get_settings()
    token = s.huggingface_token or None
    return Client(space, token=token)


def _wrap_file(path: str):
    """Gradio 4+ expects files wrapped via `handle_file()`, not raw paths."""
    from gradio_client import handle_file

    return handle_file(path)


def transcribe_file_space(
    wav_path: str | Path,
    language: str = "kk",
    space: str | None = None,
) -> list[HFSegment]:
    """Send a single WAV file to the Gradio Space and parse its JSON response."""
    repo = space or DEFAULT_SPACE
    path = str(wav_path)
    log.info("hf_space.call", space=repo, lang=language, bytes=Path(path).stat().st_size)
    client = _client(repo)
    raw = client.predict(audio_path=_wrap_file(path), language=language or "kk", api_name="/predict")

    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="replace")
    if not isinstance(raw, str):
        raw = json.dumps(raw, ensure_ascii=False)

    text = ""
    chunks = []
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            text = (data.get("text") or "").strip()
            chunks = data.get("chunks") or []
    except json.JSONDecodeError:
        # Plain text fallback.
        text = raw.strip()

    segs: list[HFSegment] = []
    if chunks:
        for c in chunks:
            ts = c.get("timestamp") or [0, 0]
            start_s = float(ts[0] or 0)
            end_s = float(ts[1] or start_s)
            segs.append(HFSegment(
                start_ms=int(start_s * 1000),
                end_ms=int(end_s * 1000),
                text=(c.get("text") or "").strip(),
                language=language,
                avg_logprob=-0.2,
                no_speech_prob=0.0,
            ))
    elif text:
        segs.append(HFSegment(
            start_ms=0,
            end_ms=0,
            text=text,
            language=language,
            avg_logprob=-0.2,
            no_speech_prob=0.0,
        ))

    log.info("hf_space.ok", space=repo, segs=len(segs), chars=sum(len(s.text) for s in segs))
    return segs
