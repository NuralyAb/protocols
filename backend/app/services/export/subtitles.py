"""SRT and WebVTT rendering for meeting audio/video playback."""
from __future__ import annotations

from typing import Any

from app.services.export.formatting import ms_to_timestamp, speaker_label, speakers_by_id


def render_srt(result: dict[str, Any]) -> bytes:
    spk_map = speakers_by_id(result)
    lines: list[str] = []
    for i, s in enumerate(result.get("transcript") or [], 1):
        start = int(s.get("start_time") or 0)
        end = max(int(s.get("end_time") or (start + 1000)), start + 500)
        label = speaker_label(s.get("speaker", ""), spk_map)
        text = (s.get("text") or "").strip().replace("\r\n", "\n")
        lines.append(str(i))
        lines.append(f"{ms_to_timestamp(start, ',')} --> {ms_to_timestamp(end, ',')}")
        lines.append(f"{label}: {text}")
        lines.append("")
    return ("\n".join(lines)).encode("utf-8")


def render_vtt(result: dict[str, Any]) -> bytes:
    spk_map = speakers_by_id(result)
    lines: list[str] = ["WEBVTT", ""]
    for s in result.get("transcript") or []:
        start = int(s.get("start_time") or 0)
        end = max(int(s.get("end_time") or (start + 1000)), start + 500)
        label = speaker_label(s.get("speaker", ""), spk_map)
        text = (s.get("text") or "").strip().replace("\r\n", "\n")
        lines.append(f"{ms_to_timestamp(start, '.')} --> {ms_to_timestamp(end, '.')}")
        lines.append(f"<v {label}>{text}</v>")
        lines.append("")
    return ("\n".join(lines)).encode("utf-8")
