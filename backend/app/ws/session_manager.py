"""In-process WS connection registry + Redis pub/sub bridge.

Scales to a single API replica. For multi-replica, Redis pub/sub already fans out,
so each API instance forwards only its own WS clients.
"""
from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any

from fastapi import WebSocket
from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger("ws.sessions")

CHANNEL = "session:{sid}"


class SessionHub:
    def __init__(self) -> None:
        self._clients: dict[str, set[WebSocket]] = defaultdict(set)
        self._redis: Redis | None = None
        self._pubsub_task: asyncio.Task | None = None

    async def start(self) -> None:
        self._redis = Redis.from_url(get_settings().redis_url, decode_responses=True)
        self._pubsub_task = asyncio.create_task(self._listen(), name="session-pubsub")

    async def stop(self) -> None:
        if self._pubsub_task:
            self._pubsub_task.cancel()
        if self._redis:
            await self._redis.aclose()

    async def attach(self, session_id: str, ws: WebSocket) -> None:
        self._clients[session_id].add(ws)
        log.info("ws.attached", sid=session_id, total=len(self._clients[session_id]))

    async def detach(self, session_id: str, ws: WebSocket) -> None:
        self._clients[session_id].discard(ws)
        if not self._clients[session_id]:
            self._clients.pop(session_id, None)

    async def publish(self, session_id: str, event: dict[str, Any]) -> None:
        if not self._redis:
            return
        await self._redis.publish(CHANNEL.format(sid=session_id), json.dumps(event))

    async def _listen(self) -> None:
        assert self._redis
        pubsub = self._redis.pubsub()
        await pubsub.psubscribe(CHANNEL.format(sid="*"))
        log.info("pubsub.listening")
        try:
            async for msg in pubsub.listen():
                if msg.get("type") != "pmessage":
                    continue
                channel = msg.get("channel") or ""
                sid = channel.split(":", 1)[1] if ":" in channel else ""
                try:
                    payload = json.loads(msg.get("data") or "{}")
                except json.JSONDecodeError:
                    continue
                clients = len(self._clients.get(sid, ()))
                log.info("pubsub.rx", sid=sid, type=payload.get("type"), clients=clients)
                await self._fanout(sid, payload)
        except asyncio.CancelledError:
            pass
        finally:
            try:
                await pubsub.aclose()
            except Exception:  # noqa: BLE001
                pass

    async def _fanout(self, session_id: str, event: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        for ws in list(self._clients.get(session_id, ())):
            try:
                await ws.send_json(event)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            await self.detach(session_id, ws)


hub = SessionHub()
