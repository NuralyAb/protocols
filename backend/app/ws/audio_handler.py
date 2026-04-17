"""Per-session audio accumulator + utterance chopper.

Client streams raw PCM16 mono 16 kHz. We buffer and emit an utterance whenever:
  - silence ≥ SILENCE_MS is detected (via trailing-RMS heuristic), OR
  - buffer grows beyond MAX_UTTERANCE_MS.

Silero VAD would be more accurate, but it requires torch in the API container. The
RMS-tail trick works well enough for 16 kHz speech; the worker then runs proper VAD
inside Whisper itself (``vad_filter=True``).
"""
from __future__ import annotations

import asyncio
import base64
import io
import struct
import time
import uuid

import numpy as np
from celery import Celery

from app.core.config import get_settings
from app.core.logging import get_logger
from app.ws.session_manager import hub

log = get_logger("ws.audio")

SAMPLE_RATE = 16_000
FRAME_MS = 40
FRAME_SAMPLES = SAMPLE_RATE * FRAME_MS // 1000  # 640
# Whisper quality vs. latency trade-off: longer chunks = cleaner output,
# shorter = faster feedback. ~1s silence + ~1s min works well for conversational speech.
SILENCE_MS = 1000
MIN_UTTERANCE_MS = 1000
MAX_UTTERANCE_MS = 20_000
# int16 RMS below this = silence. Some mics (especially browser getUserMedia
# with echo cancellation) produce very quiet PCM; 100 is conservative enough
# to catch normal speech without triggering on background hum.
RMS_THRESHOLD = 100.0


def _rms(frame: np.ndarray) -> float:
    if frame.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(frame.astype(np.float32) ** 2)))


def _celery() -> Celery:
    s = get_settings()
    return Celery("client", broker=s.celery_broker_url, backend=s.celery_result_backend)


def _pcm16_to_wav_bytes(pcm: np.ndarray, sample_rate: int = SAMPLE_RATE) -> bytes:
    """Wrap int16 PCM in a minimal RIFF/WAV container (no external deps)."""
    buf = io.BytesIO()
    n_bytes = pcm.size * 2
    # RIFF header
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + n_bytes))
    buf.write(b"WAVE")
    # fmt chunk
    buf.write(b"fmt ")
    buf.write(struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16))
    # data chunk
    buf.write(b"data")
    buf.write(struct.pack("<I", n_bytes))
    buf.write(pcm.astype("<i2").tobytes())
    return buf.getvalue()


class SessionStream:
    __slots__ = (
        "session_id", "language", "user_id", "prefer_kazakh", "use_hf", "use_space",
        "_buf", "_t0", "_last_voice_ms", "_silence_ms",
        "_voiced", "_lock", "_celery", "_utt_offset_ms",
    )

    def __init__(
        self,
        session_id: str,
        user_id: str,
        language: str | None = None,
        prefer_kazakh: bool = False,
        use_hf: bool = False,
        use_space: bool = False,
    ) -> None:
        self.session_id = session_id
        self.user_id = user_id
        self.language = language
        self.prefer_kazakh = prefer_kazakh
        self.use_hf = use_hf
        self.use_space = use_space
        self._buf: list[np.ndarray] = []
        self._t0 = time.monotonic()
        self._last_voice_ms = 0
        self._silence_ms = 0
        self._voiced = False
        self._utt_offset_ms = 0
        self._lock = asyncio.Lock()
        self._celery = _celery()

    def _buffered_ms(self) -> int:
        n = sum(a.size for a in self._buf)
        return int(n / SAMPLE_RATE * 1000)

    async def feed_pcm16(self, data: bytes) -> None:
        """Append raw little-endian int16 samples from the client."""
        if not data:
            return
        arr = np.frombuffer(data, dtype="<i2")
        async with self._lock:
            # Slice into 40ms frames to measure silence.
            extra = arr.size % FRAME_SAMPLES
            head, tail = (arr, np.empty(0, dtype="<i2"))
            if extra:
                head = arr[: arr.size - extra]
                tail = arr[arr.size - extra :]
            frames = head.reshape(-1, FRAME_SAMPLES) if head.size else np.empty((0, FRAME_SAMPLES))
            for fr in frames:
                rms = _rms(fr)
                if rms >= RMS_THRESHOLD:
                    self._silence_ms = 0
                    self._voiced = True
                else:
                    self._silence_ms += FRAME_MS
                self._buf.append(fr.copy())
            if tail.size:
                self._buf.append(tail.copy())

            buffered = self._buffered_ms()
            if self._voiced and (
                (self._silence_ms >= SILENCE_MS and buffered >= MIN_UTTERANCE_MS)
                or buffered >= MAX_UTTERANCE_MS
            ):
                await self._flush_utterance()

    async def close(self) -> None:
        async with self._lock:
            # Flush whatever's left — even if VAD never triggered. Browsers
            # with aggressive noise suppression can produce PCM so quiet that
            # RMS never crosses the threshold, and we'd drop the whole session.
            if self._buffered_ms() >= MIN_UTTERANCE_MS:
                self._voiced = True  # force flush regardless of VAD state
                await self._flush_utterance()

    async def _flush_utterance(self) -> None:
        pcm = np.concatenate(self._buf) if self._buf else np.empty(0, dtype="<i2")
        self._buf.clear()
        dur_ms = int(pcm.size / SAMPLE_RATE * 1000)
        start_ms = self._utt_offset_ms
        self._utt_offset_ms += dur_ms
        self._voiced = False
        self._silence_ms = 0
        if dur_ms < MIN_UTTERANCE_MS:
            return

        wav = _pcm16_to_wav_bytes(pcm)
        b64 = base64.b64encode(wav).decode("ascii")

        # Let the client know something is on the way (poor-man's "partial").
        await hub.publish(
            self.session_id,
            {"type": "utterance_queued", "start_ms": start_ms, "end_ms": start_ms + dur_ms},
        )

        self._celery.send_task(
            "app.workers.tasks.transcribe_utterance",
            args=[
                self.session_id,
                self.user_id,
                b64,
                start_ms,
                start_ms + dur_ms,
                self.language,
                self.prefer_kazakh,
                self.use_hf,
                self.use_space,
            ],
            queue="asr",
        )
        log.info("utterance.enqueued", sid=self.session_id, ms=dur_ms)
