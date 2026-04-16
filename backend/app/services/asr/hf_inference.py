"""HuggingFace Inference API wrapper for hosted ASR models.

Sends raw audio bytes to ``https://api-inference.huggingface.co/models/<repo>``
and returns Whisper-compatible segments. Model runs on HF GPUs — no local
conversion or weights needed.

Free tier: ~30 000 requests/month, often cold-starts (first call ~30 s).
Paid Inference Endpoints: dedicated, no cold starts.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger("asr.hf")

DEFAULT_MODEL = "Uali/whisper-turbo-ksc2-kazakh-finetuned"
ENDPOINT = "https://api-inference.huggingface.co/models/{model}"


@dataclass(slots=True)
class HFSegment:
    start_ms: int
    end_ms: int
    text: str
    language: str
    avg_logprob: float
    no_speech_prob: float


def _headers() -> dict:
    s = get_settings()
    if not s.huggingface_token:
        raise RuntimeError("HUGGINGFACE_TOKEN not configured")
    return {
        "Authorization": f"Bearer {s.huggingface_token}",
        "Content-Type": "audio/wav",
    }


def transcribe_file_hf(
    wav_path: str | Path,
    model: str | None = None,
    language: str = "kk",
    max_retries: int = 3,
) -> list[HFSegment]:
    """Send a single WAV file to HF Inference API. Audio must be ≤ ~30 MB."""
    s = get_settings()
    repo = model or s.asr_kazakh_model or DEFAULT_MODEL
    url = ENDPOINT.format(model=repo)
    payload = Path(wav_path).read_bytes()

    delay = 5.0
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=120) as client:
                r = client.post(url, headers=_headers(), content=payload)
            if r.status_code == 503:
                # Cold start — model loading. Server tells us estimated time.
                est = (r.json() or {}).get("estimated_time", delay)
                wait = min(60.0, float(est) + 1)
                log.info("hf.cold_start", repo=repo, wait_s=wait, attempt=attempt + 1)
                time.sleep(wait)
                continue
            if r.status_code == 429:
                log.warning("hf.rate_limited", repo=repo)
                time.sleep(delay)
                delay *= 2
                continue
            if r.status_code >= 400:
                raise RuntimeError(f"HF {r.status_code}: {r.text[:300]}")
            data = r.json()
            text = (data.get("text") or "").strip() if isinstance(data, dict) else str(data).strip()
            chunks = data.get("chunks") if isinstance(data, dict) else None
            if not text and not chunks:
                return []

            segs: list[HFSegment] = []
            if chunks:
                for c in chunks:
                    ts = c.get("timestamp") or [0, 0]
                    segs.append(HFSegment(
                        start_ms=int((ts[0] or 0) * 1000),
                        end_ms=int((ts[1] or ts[0] or 0) * 1000),
                        text=(c.get("text") or "").strip(),
                        language=language,
                        avg_logprob=-0.2,
                        no_speech_prob=0.0,
                    ))
            else:
                segs.append(HFSegment(
                    start_ms=0,
                    end_ms=0,
                    text=text,
                    language=language,
                    avg_logprob=-0.2,
                    no_speech_prob=0.0,
                ))
            log.info("hf.ok", repo=repo, segs=len(segs), chars=sum(len(s.text) for s in segs))
            return segs
        except (httpx.HTTPError, RuntimeError) as e:
            last_err = e
            log.warning("hf.attempt_failed", attempt=attempt + 1, error=str(e)[:200])
            time.sleep(delay)
            delay *= 1.5
    raise RuntimeError(f"HF Inference exhausted: {last_err}")
