"""HTML → PDF via WeasyPrint. System Noto fonts cover kk/ru/en."""
from __future__ import annotations

from typing import Any

from app.services.export.html_template import render_html


def render_pdf(result: dict[str, Any]) -> bytes:
    from weasyprint import HTML

    html = render_html(result)
    return HTML(string=html).write_pdf()
