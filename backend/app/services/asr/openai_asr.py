"""OpenAI cloud ASR.

Two entrypoints:
  - ``transcribe_file_openai``  — offline transcription (gpt-4o-transcribe / whisper-1)
  - Realtime streaming lives in ``app.ws.openai_bridge`` (different protocol).
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger("asr.openai")

# OpenAI accepts up to 25 MB per request. Leave margin.
MAX_FILE_BYTES = 24 * 1024 * 1024


@dataclass(slots=True)
class OpenAISegment:
    start_ms: int
    end_ms: int
    text: str
    language: str
    avg_logprob: float
    no_speech_prob: float


def _client():
    from openai import OpenAI

    s = get_settings()
    if not s.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    return OpenAI(api_key=s.openai_api_key)


_PROMPTS = {
    "kk": "Жиналыс хаттамасы. Төраға, хатшы, шешім, дауыс беру, қабылданды, қалыс қалды.",
    "ru": "Протокол заседания. Председатель, секретарь, решение, голосование, принято.",
    "en": "Meeting minutes. Chair, secretary, motion, decision, vote results.",
}


def _split_audio(wav_path: Path, chunk_sec: int = 900) -> list[tuple[Path, int]]:
    """Split a long WAV into ≤25MB chunks. Returns [(path, offset_ms), ...]."""
    size = wav_path.stat().st_size
    if size <= MAX_FILE_BYTES:
        return [(wav_path, 0)]

    # ffprobe for duration
    dur = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(wav_path),
        ],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    total_sec = int(float(dur))
    out: list[tuple[Path, int]] = []
    idx = 0
    for start in range(0, total_sec, chunk_sec):
        chunk = wav_path.with_name(f"{wav_path.stem}.chunk{idx:03d}.wav")
        subprocess.run(
            [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-ss", str(start), "-i", str(wav_path),
                "-t", str(chunk_sec), "-ac", "1", "-ar", "16000",
                "-c:a", "pcm_s16le", str(chunk),
            ],
            check=True,
        )
        out.append((chunk, start * 1000))
        idx += 1
    return out


def _call_openai(wav: Path, model: str, language: str | None):
    from openai import APIError, RateLimitError  # noqa: F401 (caller catches)

    client = _client()
    with open(wav, "rb") as f:
        kwargs = {
            "file": f,
            "model": model,
            "response_format": "verbose_json",
        }
        if language:
            kwargs["language"] = language
            if language in _PROMPTS:
                kwargs["prompt"] = _PROMPTS[language]
        # gpt-4o-transcribe supports segment timestamps; whisper-1 always does.
        if model != "gpt-4o-mini-transcribe":
            kwargs["timestamp_granularities"] = ["segment"]
        return client.audio.transcriptions.create(**kwargs)


def transcribe_file_openai(
    wav_path: str | Path,
    language: str | None = None,
) -> list[OpenAISegment]:
    """Transcribe a WAV via OpenAI with automatic chunking + model fallback."""
    from openai import APIError, RateLimitError

    s = get_settings()
    wav = Path(wav_path)
    chunks = _split_audio(wav)

    all_segs: list[OpenAISegment] = []
    used_model: str | None = None

    for chunk_path, offset_ms in chunks:
        resp = None
        last_err: Exception | None = None
        for model in (s.openai_asr_model, s.openai_asr_fallback):
            try:
                log.info("openai.asr.call", model=model, path=str(chunk_path.name), offset_ms=offset_ms)
                resp = _call_openai(chunk_path, model, language)
                used_model = model
                break
            except RateLimitError as e:
                last_err = e
                log.warning("openai.asr.rate_limited", model=model)
                continue
            except APIError as e:
                last_err = e
                log.warning("openai.asr.api_error", model=model, error=str(e)[:200])
                continue
        if resp is None:
            raise RuntimeError(f"OpenAI ASR exhausted: {last_err}") from last_err

        detected_lang = getattr(resp, "language", None) or language or "unknown"
        segments = getattr(resp, "segments", None) or []
        if not segments:
            # gpt-4o-mini-transcribe or models without timestamps → single segment
            text = (getattr(resp, "text", "") or "").strip()
            if text:
                all_segs.append(OpenAISegment(
                    start_ms=offset_ms,
                    end_ms=offset_ms + 5000,
                    text=text,
                    language=detected_lang,
                    avg_logprob=-0.2,
                    no_speech_prob=0.0,
                ))
        else:
            for seg in segments:
                all_segs.append(OpenAISegment(
                    start_ms=int((seg.start or 0) * 1000) + offset_ms,
                    end_ms=int((seg.end or (seg.start or 0) + 2) * 1000) + offset_ms,
                    text=(seg.text or "").strip(),
                    language=detected_lang,
                    avg_logprob=float(getattr(seg, "avg_logprob", -0.2) or -0.2),
                    no_speech_prob=float(getattr(seg, "no_speech_prob", 0.0) or 0.0),
                ))

    # Cleanup chunk files (but not the original)
    for chunk_path, _ in chunks:
        if chunk_path != wav:
            try:
                chunk_path.unlink(missing_ok=True)
            except OSError:
                pass

    log.info("openai.asr.done", segments=len(all_segs), model=used_model)
    return all_segs
