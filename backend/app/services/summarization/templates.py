"""Protocol-template loader.

Reads `образцы/manifest.json` + `<id>.md` files from the configured
directory. Each `.md` is YAML-frontmatter + markdown body; the body is
what the LLM fills.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger("templates")

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)


@dataclass(frozen=True)
class TemplateMeta:
    id: str
    name: str
    description: str
    language: str


@dataclass(frozen=True)
class Template:
    meta: TemplateMeta
    body: str
    sections: tuple[str, ...]


_cache: dict[str, Template] | None = None
_lock = Lock()


def _resolve_dir() -> Path:
    s = get_settings()
    if s.templates_dir:
        return Path(s.templates_dir)
    # Repo root sits above `backend/` — this file is backend/app/services/summarization/templates.py,
    # so parents[4] is the repo root.
    repo_root = Path(__file__).resolve().parents[4]
    return repo_root / "образцы"


def _parse_frontmatter(raw: str) -> tuple[dict, str]:
    m = _FRONTMATTER_RE.match(raw)
    if not m:
        return {}, raw
    meta_block, body = m.group(1), m.group(2)
    # Tiny YAML subset: `key: value` and `key:\n  - item\n  - item`
    meta: dict = {}
    current_list_key: str | None = None
    for line in meta_block.splitlines():
        if not line.strip():
            current_list_key = None
            continue
        if line.startswith("  - "):
            if current_list_key:
                meta.setdefault(current_list_key, []).append(line[4:].strip())
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if val == "":
                current_list_key = key
                meta[key] = []
            else:
                current_list_key = None
                meta[key] = val
    return meta, body


def _load() -> dict[str, Template]:
    base = _resolve_dir()
    out: dict[str, Template] = {}
    manifest_path = base / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for entry in manifest.get("templates", []):
            fp = base / entry["file"]
            if not fp.exists():
                log.warning("templates.file_missing", id=entry.get("id"), file=entry.get("file"))
                continue
            raw = fp.read_text(encoding="utf-8")
            front, body = _parse_frontmatter(raw)
            meta = TemplateMeta(
                id=entry["id"],
                name=entry.get("name") or front.get("name") or entry["id"],
                description=entry.get("description") or front.get("description") or "",
                language=entry.get("language") or front.get("language") or "ru",
            )
            sections = tuple(front.get("sections") or [])
            out[entry["id"]] = Template(meta=meta, body=body.strip(), sections=sections)
    else:
        log.warning("templates.manifest_missing", path=str(manifest_path))

    custom_dir = base / "custom"
    if custom_dir.exists():
        for fp in sorted(custom_dir.glob("*.md")):
            raw = fp.read_text(encoding="utf-8")
            front, body = _parse_frontmatter(raw)
            tpl_id = str(front.get("id") or fp.stem)
            meta = TemplateMeta(
                id=tpl_id,
                name=str(front.get("name") or tpl_id),
                description=str(front.get("description") or ""),
                language=str(front.get("language") or "ru"),
            )
            sections = tuple(front.get("sections") or [])
            out[tpl_id] = Template(meta=meta, body=body.strip(), sections=sections)

    log.info("templates.loaded", count=len(out), dir=str(base))
    return out


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(value: str) -> str:
    s = _SLUG_RE.sub("-", value.lower()).strip("-")
    return s or "tpl"


def save_custom_template(
    *, name: str, description: str, language: str, body: str
) -> TemplateMeta:
    base = _resolve_dir()
    custom_dir = base / "custom"
    custom_dir.mkdir(parents=True, exist_ok=True)

    import time
    tpl_id = f"custom-{_slugify(name)}-{int(time.time())}"
    safe_name = name.replace("\n", " ").strip()[:120] or tpl_id
    safe_desc = description.replace("\n", " ").strip()[:500]
    safe_lang = (language or "ru").strip()[:8] or "ru"

    frontmatter = (
        "---\n"
        f"id: {tpl_id}\n"
        f"name: {safe_name}\n"
        f"description: {safe_desc}\n"
        f"language: {safe_lang}\n"
        "---\n"
    )
    (custom_dir / f"{tpl_id}.md").write_text(frontmatter + body.strip() + "\n", encoding="utf-8")
    reload_templates()
    return TemplateMeta(id=tpl_id, name=safe_name, description=safe_desc, language=safe_lang)


def _ensure() -> dict[str, Template]:
    global _cache
    if _cache is None:
        with _lock:
            if _cache is None:
                _cache = _load()
    return _cache


def reload_templates() -> None:
    """Force re-read from disk. Handy for tests or after manifest edits."""
    global _cache
    with _lock:
        _cache = None


def list_templates() -> list[TemplateMeta]:
    return [t.meta for t in _ensure().values()]


def get_template(template_id: str) -> Template | None:
    return _ensure().get(template_id)


__all__ = [
    "Template",
    "TemplateMeta",
    "list_templates",
    "get_template",
    "reload_templates",
    "save_custom_template",
]
