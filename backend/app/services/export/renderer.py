"""Dispatch exporter by format."""
from __future__ import annotations

from typing import Any, Callable

from app.db.models import ExportFormat
from app.services.export.docx_ import render_docx
from app.services.export.plain import render_json, render_txt
from app.services.export.subtitles import render_srt, render_vtt

# PDF is imported lazily — WeasyPrint pulls a large native stack.

CONTENT_TYPES: dict[ExportFormat, str] = {
    ExportFormat.json: "application/json",
    ExportFormat.txt: "text/plain; charset=utf-8",
    ExportFormat.srt: "application/x-subrip",
    ExportFormat.vtt: "text/vtt; charset=utf-8",
    ExportFormat.docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ExportFormat.pdf: "application/pdf",
}

_EXT: dict[ExportFormat, str] = {
    ExportFormat.json: "json",
    ExportFormat.txt: "txt",
    ExportFormat.srt: "srt",
    ExportFormat.vtt: "vtt",
    ExportFormat.docx: "docx",
    ExportFormat.pdf: "pdf",
}


def _render_pdf(result: dict[str, Any]) -> bytes:
    from app.services.export.pdf import render_pdf

    return render_pdf(result)


_RENDERERS: dict[ExportFormat, Callable[[dict[str, Any]], bytes]] = {
    ExportFormat.json: render_json,
    ExportFormat.txt: render_txt,
    ExportFormat.srt: render_srt,
    ExportFormat.vtt: render_vtt,
    ExportFormat.docx: render_docx,
    ExportFormat.pdf: _render_pdf,
}


def render(result: dict[str, Any], fmt: ExportFormat) -> tuple[bytes, str, str]:
    """Return (bytes, content_type, file_extension)."""
    if fmt not in _RENDERERS:
        raise ValueError(f"Unsupported format: {fmt}")
    data = _RENDERERS[fmt](result or {})
    return data, CONTENT_TYPES[fmt], _EXT[fmt]
