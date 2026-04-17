"""Thin async httpx wrapper around the protocol-ai backend."""
from __future__ import annotations

import os
from typing import Any

import httpx

BACKEND_URL = os.environ.get("BOT_API_URL", "http://api:8000").rstrip("/")
TIMEOUT = httpx.Timeout(connect=10.0, read=60.0, write=30.0, pool=10.0)


class BackendError(RuntimeError):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(f"{status}: {detail}")
        self.status = status
        self.detail = detail


def _headers(token: str | None) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


async def _handle(resp: httpx.Response) -> Any:
    if resp.status_code >= 400:
        try:
            data = resp.json()
            detail = data.get("detail") if isinstance(data, dict) else str(data)
        except Exception:  # noqa: BLE001
            detail = resp.text[:300]
        raise BackendError(resp.status_code, detail or f"HTTP {resp.status_code}")
    if resp.headers.get("content-type", "").startswith("application/json"):
        return resp.json()
    return resp.content


async def login(email: str, password: str) -> str:
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.post(
            f"{BACKEND_URL}/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        data = await _handle(r)
    return data["access_token"]


async def list_sessions(token: str, limit: int = 10) -> list[dict]:
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(
            f"{BACKEND_URL}/api/v1/sessions",
            headers=_headers(token),
            params={"limit": limit},
        )
        return await _handle(r)


async def session_by_friendly_id(token: str, fid: str) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(
            f"{BACKEND_URL}/api/v1/sessions/by_friendly_id/{fid}",
            headers=_headers(token),
        )
        return await _handle(r)


async def list_templates(token: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(
            f"{BACKEND_URL}/api/v1/sessions/templates",
            headers=_headers(token),
        )
        return await _handle(r)


async def generate_protocol(
    token: str, session_id: str, template_id: str, fmt: str = "pdf"
) -> bytes:
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.post(
            f"{BACKEND_URL}/api/v1/sessions/{session_id}/protocol",
            headers=_headers(token),
            json={"template_id": template_id, "format": fmt},
        )
        if r.status_code >= 400:
            await _handle(r)  # raises
        return r.content


async def insights(token: str, session_id: str) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(
            f"{BACKEND_URL}/api/v1/sessions/{session_id}/insights",
            headers=_headers(token),
        )
        return await _handle(r)


async def list_jobs(token: str, limit: int = 10) -> list[dict]:
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(
            f"{BACKEND_URL}/api/v1/jobs",
            headers=_headers(token),
            params={"limit": limit},
        )
        return await _handle(r)


async def job_by_friendly_id(token: str, fid: str) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(
            f"{BACKEND_URL}/api/v1/jobs/by_friendly_id/{fid}",
            headers=_headers(token),
        )
        return await _handle(r)


async def generate_job_protocol(
    token: str, job_id: str, template_id: str, fmt: str = "pdf"
) -> bytes:
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.post(
            f"{BACKEND_URL}/api/v1/jobs/{job_id}/protocol",
            headers=_headers(token),
            json={"template_id": template_id, "format": fmt},
        )
        if r.status_code >= 400:
            await _handle(r)
        return r.content


async def job_insights(token: str, job_id: str) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(
            f"{BACKEND_URL}/api/v1/jobs/{job_id}/insights",
            headers=_headers(token),
        )
        return await _handle(r)


async def qa(token: str, session_id: str, question: str, lang: str) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(
            f"{BACKEND_URL}/api/v1/sessions/{session_id}/qa",
            headers=_headers(token),
            params={"question": question, "lang": lang},
        )
        return await _handle(r)
