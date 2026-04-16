"""Shared formatting helpers for exporters."""
from __future__ import annotations

from typing import Any


def ms_to_timestamp(ms: int, sep: str = ",") -> str:
    """Format milliseconds as `HH:MM:SS{sep}mmm` (sep is ',' for SRT, '.' for VTT)."""
    if ms < 0:
        ms = 0
    hours, rem = divmod(ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}{sep}{millis:03d}"


def ms_to_clock(ms: int) -> str:
    """Shorter `HH:MM:SS` (or `MM:SS`) for human-readable rendering."""
    hours, rem = divmod(ms // 1000, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def speaker_label(
    speaker_id: str,
    speakers_by_id: dict[str, dict[str, Any]] | None,
) -> str:
    if not speakers_by_id:
        return speaker_id
    entry = speakers_by_id.get(speaker_id)
    if not entry:
        return speaker_id
    label = entry.get("label") or speaker_id
    role = entry.get("role")
    return f"{label} ({role})" if role else label


def speakers_by_id(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    participants = (result.get("protocol") or {}).get("participants") or []
    return {p.get("id"): p for p in participants if p.get("id")}


def result_title(result: dict[str, Any], fallback: str = "Протокол заседания") -> str:
    return (result.get("protocol") or {}).get("title") or fallback
