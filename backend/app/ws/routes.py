"""WebSocket endpoints."""
from __future__ import annotations

import asyncio
import json as _json
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import decode_token
from app.db.models import LiveSession, TranscriptSegment
from app.db.session import SessionLocal
from app.ws.audio_handler import SessionStream
from app.ws.openai_bridge import OpenAIBridge
from app.ws.session_manager import hub

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
        await _run_openai_bridge(websocket, session, language)
    else:
        await _run_local(
            websocket, session, user_id, language,
            prefer_kazakh=prefer_kazakh, use_hf=use_hf,
        )

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
    try:
        while True:
            msg = await websocket.receive()
            if msg.get("type") == "websocket.disconnect":
                break
            if "bytes" in msg and msg["bytes"] is not None:
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


async def _run_openai_bridge(websocket: WebSocket, session: LiveSession, language: str | None) -> None:
    bridge = OpenAIBridge(session_id=str(session.id), language=language)
    try:
        await bridge.start()
    except Exception as e:  # noqa: BLE001
        log.exception("openai_bridge.start_failed")
        await websocket.send_json({"type": "error", "message": f"openai_failed: {e}"})
        return

    async def forward_events() -> None:
        async for ev in bridge.events():
            try:
                await websocket.send_json(ev)
            except Exception:  # noqa: BLE001
                break
            if ev.get("type") == "final":
                try:
                    await _persist_final(session.id, ev)
                except Exception as e:  # noqa: BLE001
                    log.exception("persist_final_failed", error=str(e))

    fwd_task = asyncio.create_task(forward_events())
    try:
        while True:
            msg = await websocket.receive()
            if msg.get("type") == "websocket.disconnect":
                break
            if "bytes" in msg and msg["bytes"] is not None:
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
