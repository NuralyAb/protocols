"""Plain-text and JSON renderers."""
from __future__ import annotations

import json
from typing import Any

from app.services.export.formatting import (
    ms_to_clock,
    result_title,
    speaker_label,
    speakers_by_id,
)
from app.services.export.html_template import LABELS, _pick_lang


def render_json(result: dict[str, Any]) -> bytes:
    return json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8")


def render_txt(result: dict[str, Any]) -> bytes:
    lang = _pick_lang(result)
    L = LABELS[lang]
    proto = result.get("protocol") or {}
    meta = result.get("metadata") or {}
    spk = speakers_by_id(result)

    out: list[str] = []
    out.append(result_title(result))
    out.append("=" * len(out[-1]))
    if proto.get("date"):
        out.append(f"{L['date']}: {proto['date']}")
    out.append(f"{L['duration']}: {ms_to_clock(int(meta.get('duration_ms') or 0))}")
    out.append(f"{L['languages']}: {', '.join(meta.get('languages_detected') or []) or '—'}")
    out.append("")

    if proto.get("participants"):
        out.append(L["participants"])
        for p in proto["participants"]:
            role = f" — {p['role']}" if p.get("role") else ""
            out.append(f"  • {p.get('label') or p.get('id')}{role}")
        out.append("")

    if proto.get("agenda"):
        out.append(L["agenda"])
        for i, a in enumerate(proto["agenda"], 1):
            out.append(f"  {i}. {a}")
        out.append("")

    if proto.get("discussion"):
        out.append(L["discussion"])
        for d in proto["discussion"]:
            out.append(f"  • {d.get('topic')}: {d.get('summary', '')}")
        out.append("")

    if proto.get("decisions"):
        out.append(L["decisions"])
        for i, dec in enumerate(proto["decisions"], 1):
            votes = dec.get("votes") or {}
            tail = ""
            if votes:
                tail = (
                    f" ({L['v_for']}: {votes.get('for', 0)}, "
                    f"{L['v_against']}: {votes.get('against', 0)}, "
                    f"{L['v_abstain']}: {votes.get('abstain', 0)})"
                )
            out.append(f"  {i}. {dec.get('text', '')}{tail}")
        out.append("")

    if proto.get("action_items"):
        out.append(L["actions"])
        for a in proto["action_items"]:
            parts = [a.get("task") or ""]
            if a.get("assignee"):
                parts.append(f"{L['a_assignee']}: {a['assignee']}")
            if a.get("deadline"):
                parts.append(f"{L['a_deadline']}: {a['deadline']}")
            out.append(f"  • {' — '.join(parts)}")
        out.append("")

    out.append(L["transcript"])
    out.append("-" * len(L["transcript"]))
    for s in result.get("transcript") or []:
        label = speaker_label(s.get("speaker", ""), spk)
        ts = ms_to_clock(int(s.get("start_time") or 0))
        lang_tag = f" ({s['language']})" if s.get("language") else ""
        out.append(f"[{ts}] {label}{lang_tag}: {s.get('text') or ''}")

    return ("\n".join(out) + "\n").encode("utf-8")
