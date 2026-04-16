"""Bridge: browser WS ↔ OpenAI Realtime WS.

Protocol docs: https://platform.openai.com/docs/guides/realtime

Forwards:
  - inbound PCM16 16 kHz chunks → ``input_audio_buffer.append``
  - OpenAI ``conversation.item.input_audio_transcription.delta`` → our ``partial``
  - OpenAI ``conversation.item.input_audio_transcription.completed`` → our ``final``
"""
from __future__ import annotations

import asyncio
import base64
import json
import time
from typing import AsyncIterator

import websockets

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger("ws.openai_bridge")


class OpenAIBridge:
    __slots__ = ("session_id", "language", "_ws", "_outbox", "_reader", "_started_at")

    def __init__(self, session_id: str, language: str | None = None) -> None:
        self.session_id = session_id
        self.language = language if language in ("kk", "ru", "en") else None
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._outbox: asyncio.Queue[dict | None] = asyncio.Queue()
        self._reader: asyncio.Task | None = None
        self._started_at: float = 0.0

    async def start(self) -> None:
        s = get_settings()
        if not s.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        url = f"wss://api.openai.com/v1/realtime?model={s.openai_realtime_model}"
        self._ws = await websockets.connect(
            url,
            additional_headers={
                "Authorization": f"Bearer {s.openai_api_key}",
                "OpenAI-Beta": "realtime=v1",
            },
            max_size=16 * 1024 * 1024,
            ping_interval=20,
        )
        self._started_at = time.monotonic()

        # NB: we intentionally don't set `prompt` — on short/silent utterances the
        # model echoes it back verbatim ("Жиналыс хаттамасы..."), which looks like
        # transcription but isn't. Skip prompt; language alone is enough.
        transcription: dict = {"model": "gpt-4o-transcribe"}
        if self.language:
            transcription["language"] = self.language

        await self._ws.send(json.dumps({
            "type": "session.update",
            "session": {
                "modalities": ["text"],
                "input_audio_format": "pcm16",
                "input_audio_transcription": transcription,
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 600,
                },
            },
        }))
        self._reader = asyncio.create_task(self._read_loop(), name="openai-bridge-read")
        log.info("openai_bridge.started", sid=self.session_id, lang=self.language)

    async def feed_pcm16(self, chunk: bytes) -> None:
        if not self._ws or not chunk:
            return
        b64 = base64.b64encode(chunk).decode("ascii")
        try:
            await self._ws.send(json.dumps({"type": "input_audio_buffer.append", "audio": b64}))
        except websockets.ConnectionClosed:
            await self._outbox.put({"type": "error", "message": "openai_ws_closed"})

    async def close(self) -> None:
        if self._ws:
            try:
                await self._ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
                await self._ws.close()
            except Exception:  # noqa: BLE001
                pass
            self._ws = None
        if self._reader:
            self._reader.cancel()
            self._reader = None

    async def events(self) -> AsyncIterator[dict]:
        """Yield translated events for the browser. Returns when bridge closes."""
        while True:
            ev = await self._outbox.get()
            if ev is None:
                return
            yield ev

    async def _read_loop(self) -> None:
        assert self._ws
        try:
            async for raw in self._ws:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                t = msg.get("type", "")
                now_ms = int((time.monotonic() - self._started_at) * 1000)

                if t == "conversation.item.input_audio_transcription.delta":
                    await self._outbox.put({
                        "type": "partial",
                        "text": msg.get("delta", ""),
                        "start_ms": now_ms,
                    })
                elif t == "conversation.item.input_audio_transcription.completed":
                    text = (msg.get("transcript") or "").strip()
                    if not text:
                        continue
                    await self._outbox.put({
                        "type": "final",
                        "text": text,
                        "start_ms": now_ms,
                        "end_ms": now_ms,
                        "speaker": "SPEAKER_00",
                        "language": self.language or "unknown",
                        "confidence": None,
                    })
                # Skip "speech_started" — partials already act as "speaking now"
                # indicator. Sending utterance_queued without matching timecodes
                # leaves orphan "…" entries on the client.
                elif t == "error":
                    err = msg.get("error", {})
                    log.warning("openai_bridge.error", error=err)
                    await self._outbox.put({
                        "type": "error",
                        "message": err.get("message") or "openai_error",
                    })
        except asyncio.CancelledError:
            pass
        except websockets.ConnectionClosed as e:
            log.info("openai_bridge.closed", code=e.code, reason=str(e.reason)[:100])
        finally:
            await self._outbox.put(None)
