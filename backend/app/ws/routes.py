"""WebSocket endpoints."""
from __future__ import annotations

import asyncio
import json as _json
import uuid
from datetime import datetime, timezone
from io import BytesIO

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import decode_token
from app.db.models import LiveSession, TranscriptSegment
from app.db.session import SessionLocal
from app.services.diarization.online import (
    assign_speaker_async,
    reset_session as diar_reset_session,
)
from app.services.storage.s3_service import upload_fileobj
from app.ws.audio_handler import SessionStream, _pcm16_to_wav_bytes
from app.ws.openai_bridge import OpenAIBridge
from app.ws.session_manager import hub

import numpy as np

_DIAR_WINDOW_SEC = 6
_DIAR_SAMPLE_RATE = 16_000

router = APIRouter()
log = get_logger("ws.routes")


async def _auth_session(ws: WebSocket, session_id: str, token: str) -> tuple[str, LiveSession] | None:
    try:
        payload = decode_token(token)
    except ValueError:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
    user_id = payload.get("sub")
    if not user_id or payload.get("type") != "access":
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
    async with SessionLocal() as db:
        session = await db.scalar(
            select(LiveSession).where(LiveSession.id == sid, LiveSession.owner_id == user_id)
        )
    if not session:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
    return user_id, session


async def _auth_public_session(ws: WebSocket, session_id: str, token: str) -> LiveSession | None:
    """Validate a viewer token (opaque, stored on LiveSession)."""
    if not token:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
    async with SessionLocal() as db:
        session = await db.scalar(
            select(LiveSession).where(
                LiveSession.id == sid,
                LiveSession.viewer_token == token,
            )
        )
    if not session:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
    return session


async def _finalize_session(session_id: uuid.UUID, user_id: str, pcm_bytes: bytearray) -> None:
    """On disconnect: persist full recording as WAV + mark session ended."""
    settings = get_settings()
    audio_key: str | None = None
    if pcm_bytes:
        try:
            pcm = np.frombuffer(bytes(pcm_bytes), dtype="<i2")
            wav = _pcm16_to_wav_bytes(pcm)
            audio_key = f"sessions/{user_id}/{session_id}.wav"
            await upload_fileobj(
                settings.s3_bucket_media, audio_key, BytesIO(wav), content_type="audio/wav"
            )
        except Exception as e:  # noqa: BLE001
            log.warning("session.audio_upload_failed", sid=str(session_id), err=str(e))
            audio_key = None

    async with SessionLocal() as db:
        s = await db.scalar(select(LiveSession).where(LiveSession.id == session_id))
        if not s:
            return
        s.is_active = False
        s.ended_at = datetime.now(timezone.utc)
        if audio_key:
            s.audio_key = audio_key
        await db.commit()


async def _persist_final(session_id: uuid.UUID, event: dict) -> None:
    async with SessionLocal() as db:
        db.add(TranscriptSegment(
            session_id=session_id,
            speaker_diarization_id=event.get("speaker") or "SPEAKER_00",
            language=event.get("language"),
            start_ms=int(event.get("start_ms") or 0),
            end_ms=int(event.get("end_ms") or (event.get("start_ms") or 0) + 1000),
            text=event.get("text") or "",
            confidence=event.get("confidence"),
        ))
        await db.commit()


@router.websocket("/ws/session/{session_id}")
async def session_ws(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(..., description="JWT access token"),
) -> None:
    await websocket.accept()
    authed = await _auth_session(websocket, session_id, token)
    if not authed:
        return
    user_id, session = authed
    language = None
    if session.languages and len(session.languages) == 1:
        language = session.languages[0]

    settings = get_settings()
    provider = getattr(session, "asr_provider", "local") or "local"
    use_openai = provider == "openai" and bool(settings.openai_api_key)
    prefer_kazakh = provider == "local_kazakh"
    use_hf = provider == "hf_kazakh"

    await hub.attach(session_id, websocket)
    await websocket.send_json({
        "type": "ready",
        "session_id": session_id,
        "language": language,
        "provider": provider,
    })

    if use_openai:
        await _run_openai_bridge(websocket, session, user_id, language)
    else:
        await _run_local(
            websocket, session, user_id, language,
            prefer_kazakh=prefer_kazakh, use_hf=use_hf,
        )

    await hub.detach(session_id, websocket)


@router.websocket("/ws/public/session/{session_id}")
async def public_session_ws(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(..., description="Viewer token"),
) -> None:
    """Read-only WS for QR-code viewers.

    Validates the opaque viewer_token, attaches to the hub, and only forwards
    events. Any inbound bytes/messages from the viewer are ignored.
    """
    await websocket.accept()
    session = await _auth_public_session(websocket, session_id, token)
    if not session:
        return

    await hub.attach(session_id, websocket)
    try:
        await websocket.send_json({
            "type": "ready",
            "session_id": session_id,
            "language": (session.languages or [None])[0] if session.languages else None,
            "is_active": session.is_active,
            "viewer": True,
        })
        # Drain any messages the viewer sends — we do not allow uplink.
        while True:
            msg = await websocket.receive()
            if msg.get("type") == "websocket.disconnect":
                break
    except WebSocketDisconnect:
        pass
    finally:
        await hub.detach(session_id, websocket)


async def _run_local(
    websocket: WebSocket,
    session: LiveSession,
    user_id: str,
    language: str | None,
    prefer_kazakh: bool = False,
    use_hf: bool = False,
) -> None:
    stream = SessionStream(
        session_id=str(session.id),
        user_id=str(user_id),
        language=language,
        prefer_kazakh=prefer_kazakh,
        use_hf=use_hf,
    )
    recording = bytearray()
    try:
        while True:
            msg = await websocket.receive()
            if msg.get("type") == "websocket.disconnect":
                break
            if "bytes" in msg and msg["bytes"] is not None:
                recording.extend(msg["bytes"])
                await stream.feed_pcm16(msg["bytes"])
            elif "text" in msg and msg["text"]:
                try:
                    ev = _json.loads(msg["text"])
                except _json.JSONDecodeError:
                    continue
                if ev.get("type") == "end":
                    await stream.close()
                    await websocket.send_json({"type": "ended"})
                    break
    except WebSocketDisconnect:
        pass
    finally:
        await stream.close()
        await _finalize_session(session.id, user_id, recording)


async def _run_openai_bridge(
    websocket: WebSocket,
    session: LiveSession,
    user_id: str,
    language: str | None,
) -> None:
    bridge = OpenAIBridge(session_id=str(session.id), language=language)
    try:
        await bridge.start()
    except Exception as e:  # noqa: BLE001
        log.exception("openai_bridge.start_failed")
        await websocket.send_json({"type": "error", "message": f"openai_failed: {e}"})
        return

    recording = bytearray()

    async def forward_events() -> None:
        async for ev in bridge.events():
            if ev.get("type") == "final":
                # Cluster speaker using the last N seconds of PCM we've buffered.
                tail_bytes = _DIAR_WINDOW_SEC * _DIAR_SAMPLE_RATE * 2
                tail = bytes(recording[-tail_bytes:]) if len(recording) >= tail_bytes else bytes(recording)
                if tail:
                    try:
                        pcm = np.frombuffer(tail, dtype="<i2")
                        ev["speaker"] = await assign_speaker_async(str(session.id), pcm)
                    except Exception as e:  # noqa: BLE001
                        log.warning("diarization.assign_failed", error=str(e))
            # Publish through the hub so owner + viewers all see it via _fanout.
            try:
                await hub.publish(str(session.id), ev)
            except Exception as e:  # noqa: BLE001
                log.warning("hub.publish_failed", error=str(e))
            if ev.get("type") == "final":
                try:
                    await _persist_final(session.id, ev)
                except Exception as e:  # noqa: BLE001
                    log.exception("persist_final_failed", error=str(e))

    diar_reset_session(str(session.id))
    fwd_task = asyncio.create_task(forward_events())
    try:
        while True:
            msg = await websocket.receive()
            if msg.get("type") == "websocket.disconnect":
                break
            if "bytes" in msg and msg["bytes"] is not None:
                recording.extend(msg["bytes"])
                await bridge.feed_pcm16(msg["bytes"])
            elif "text" in msg and msg["text"]:
                try:
                    ev = _json.loads(msg["text"])
                except _json.JSONDecodeError:
                    continue
                if ev.get("type") == "end":
                    await bridge.close()
                    await websocket.send_json({"type": "ended"})
                    break
    except WebSocketDisconnect:
        pass
    finally:
        await bridge.close()
        fwd_task.cancel()
        await _finalize_session(session.id, user_id, recording)
