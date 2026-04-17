"""Command + message handlers for the Telegram bot."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from app.bot import api_client as api
from app.bot.api_client import BackendError
from app.bot.i18n import Lang, t

log = logging.getLogger("bot.handlers")


@dataclass
class UserState:
    token: str | None = None
    session_id: str | None = None
    session_title: str | None = None
    session_fid: str | None = None
    lang: Lang = "ru"


# Per-process in-memory state. For hackathon-scale usage this is fine; for prod
# swap to Redis or the backend DB via a dedicated table.
_STATE: dict[int, UserState] = {}


def _state(user_id: int) -> UserState:
    return _STATE.setdefault(user_id, UserState())


def _lang(user_id: int) -> Lang:
    return _state(user_id).lang


def _require_auth(state: UserState, user_id: int) -> str | None:
    """Return token or None (and side-effect: caller should reply with not_authed)."""
    return state.token


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    assert user is not None
    await update.effective_message.reply_text(t("welcome", _lang(user.id)))


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    assert user is not None
    await update.effective_message.reply_text(t("help", _lang(user.id)))


async def cmd_login(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    msg = update.effective_message
    assert user is not None and msg is not None
    lang = _lang(user.id)
    args = (ctx.args or [])
    if len(args) < 2:
        await msg.reply_text(t("login_usage", lang))
        return
    email, password = args[0], " ".join(args[1:])
    try:
        token = await api.login(email, password)
    except BackendError as e:
        await msg.reply_text(t("login_fail", lang, error=e.detail))
        return
    state = _state(user.id)
    state.token = token
    await msg.reply_text(t("login_ok", lang))


async def cmd_logout(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    assert user is not None
    _STATE.pop(user.id, None)
    await update.effective_message.reply_text(t("logged_out", _lang(user.id)))


async def cmd_lang(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    msg = update.effective_message
    assert user is not None and msg is not None
    args = ctx.args or []
    cur = _lang(user.id)
    if not args or args[0].lower() not in ("ru", "kk", "en"):
        await msg.reply_text(t("lang_usage", cur))
        return
    new_lang: Lang = args[0].lower()  # type: ignore[assignment]
    _state(user.id).lang = new_lang
    await msg.reply_text(t("lang_set", new_lang))


async def cmd_last(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    msg = update.effective_message
    assert user is not None and msg is not None
    state = _state(user.id)
    lang = state.lang
    if not state.token:
        await msg.reply_text(t("not_authed", lang))
        return
    try:
        sessions = await api.list_sessions(state.token, limit=10)
    except BackendError as e:
        await msg.reply_text(t("qa_fail", lang, error=e.detail))
        return
    if not sessions:
        await msg.reply_text(t("last_empty", lang))
        return
    lines = [t("last_header", lang)]
    for s in sessions:
        title = s.get("title") or s["id"][:8]
        fid = s.get("friendly_id") or "—"
        started = s.get("started_at") or ""
        try:
            started_fmt = datetime.fromisoformat(started.replace("Z", "+00:00")).strftime("%d.%m %H:%M")
        except Exception:  # noqa: BLE001
            started_fmt = started[:16]
        status = "🔴" if s.get("is_active") else "✅"
        lines.append(f"{status} `{fid}` · {title} · {started_fmt}")
    await msg.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def cmd_use(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    msg = update.effective_message
    assert user is not None and msg is not None
    state = _state(user.id)
    lang = state.lang
    if not state.token:
        await msg.reply_text(t("not_authed", lang))
        return
    args = ctx.args or []
    if not args:
        await msg.reply_text(t("use_usage", lang))
        return
    fid = args[0].strip()
    try:
        session = await api.session_by_friendly_id(state.token, fid)
    except BackendError as e:
        if e.status == 404:
            await msg.reply_text(t("not_found", lang))
        else:
            await msg.reply_text(t("qa_fail", lang, error=e.detail))
        return
    state.session_id = session["id"]
    state.session_fid = session.get("friendly_id") or fid
    state.session_title = session.get("title") or f"Live · {session['id'][:8]}"
    await msg.reply_text(
        t("use_ok", lang, title=state.session_title, fid=state.session_fid),
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_change(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    msg = update.effective_message
    assert user is not None and msg is not None
    state = _state(user.id)
    state.session_id = None
    state.session_fid = None
    state.session_title = None
    await msg.reply_text(t("change_prompt", state.lang))


async def cmd_protocol(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    msg = update.effective_message
    assert user is not None and msg is not None
    state = _state(user.id)
    lang = state.lang
    if not state.token:
        await msg.reply_text(t("not_authed", lang))
        return
    if not state.session_id:
        await msg.reply_text(t("no_session", lang))
        return

    await msg.reply_text(t("protocol_generating", lang))

    try:
        templates = await api.list_templates(state.token)
    except BackendError as e:
        await msg.reply_text(t("qa_fail", lang, error=e.detail))
        return
    if not templates:
        await msg.reply_text(t("no_template", lang))
        return
    tpl_id = templates[0]["id"]

    try:
        pdf_bytes = await api.generate_protocol(state.token, state.session_id, tpl_id, fmt="pdf")
    except BackendError as e:
        await msg.reply_text(t("protocol_fail", lang, error=e.detail))
        return

    safe_title = (state.session_title or "protocol").replace(" ", "_")
    await msg.reply_document(
        document=pdf_bytes,
        filename=f"{safe_title}.pdf",
    )


def _fmt_duration(ms: int) -> str:
    s = max(0, int(ms // 1000))
    if s >= 3600:
        return f"{s // 3600}:{(s % 3600) // 60:02d}:{s % 60:02d}"
    return f"{s // 60}:{s % 60:02d}"


async def cmd_insights(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Show speaker stats + top words + LLM key moments — good for casual talks."""
    user = update.effective_user
    msg = update.effective_message
    assert user is not None and msg is not None
    state = _state(user.id)
    lang = state.lang
    if not state.token:
        await msg.reply_text(t("not_authed", lang))
        return
    if not state.session_id:
        await msg.reply_text(t("no_session", lang))
        return

    await msg.reply_text(t("qa_thinking", lang))
    try:
        data = await api.insights(state.token, state.session_id)
    except BackendError as e:
        await msg.reply_text(t("qa_fail", lang, error=e.detail))
        return

    totals = data.get("totals") or {}
    speakers = data.get("speakers") or []
    words = data.get("top_words") or []
    moments = data.get("key_moments") or []

    if not speakers and not words:
        await msg.reply_text(t("insights_empty", lang))
        return

    parts: list[str] = [t("insights_header", lang)]
    if totals:
        parts.append(
            f"⏱ {_fmt_duration(totals.get('speaking_ms', 0))} · "
            f"👥 {totals.get('speakers', 0)} · "
            f"💬 {totals.get('segments', 0)} реплик"
        )

    if speakers:
        parts.append("")
        parts.append(t("insights_speakers", lang))
        for sp in speakers[:6]:
            label = sp.get("label") or sp.get("id") or "?"
            pct = sp.get("percentage") or 0
            ms = sp.get("speaking_ms") or 0
            parts.append(f"• *{label}* — {_fmt_duration(ms)} ({int(pct)}%)")

    if words:
        parts.append("")
        parts.append(t("insights_top_words", lang))
        top = words[:12]
        parts.append(" · ".join(f"`{w['word']}`×{w['count']}" for w in top))

    if moments:
        parts.append("")
        parts.append(t("insights_moments", lang))
        for m in moments[:6]:
            ts_ms = m.get("start_ms") or m.get("timestamp") or 0
            text = (m.get("text") or m.get("summary") or "").strip()
            if not text:
                continue
            parts.append(f"[{_mmss(int(ts_ms))}] {text}")

    body = "\n".join(parts)
    try:
        await msg.reply_text(body, parse_mode=ParseMode.MARKDOWN)
    except BadRequest:
        # Markdown failed to parse — fallback to plain.
        await msg.reply_text(body)


async def handle_question(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Free-form text → RAG question."""
    user = update.effective_user
    msg = update.effective_message
    assert user is not None and msg is not None
    text = (msg.text or "").strip()
    if not text or text.startswith("/"):
        return
    state = _state(user.id)
    lang = state.lang
    if not state.token:
        await msg.reply_text(t("not_authed", lang))
        return
    if not state.session_id:
        await msg.reply_text(t("no_session", lang))
        return

    thinking = await msg.reply_text(t("qa_thinking", lang))
    try:
        resp = await api.qa(state.token, state.session_id, text, lang)
    except BackendError as e:
        await thinking.edit_text(t("qa_fail", lang, error=e.detail))
        return
    answer = (resp.get("answer") or "").strip() or t("qa_fail", lang, error="empty")
    sources = resp.get("sources") or []
    tail = ""
    if sources:
        bits = [f"{_mmss(s.get('start_ms', 0))} {s.get('speaker', '')}".strip() for s in sources[:4]]
        tail = "\n\n— " + ", ".join(bits)
    await _safe_edit(thinking, answer + tail)


def _mmss(ms: int) -> str:
    s = max(0, int(ms // 1000))
    return f"{s // 60:02d}:{s % 60:02d}"


async def _safe_edit(msg, text: str) -> None:
    # LLM replies may contain stray *, _, ` that break MARKDOWN parsing and
    # leave the "thinking…" placeholder forever. Fall back to plain text.
    try:
        await msg.edit_text(text, parse_mode=ParseMode.MARKDOWN)
    except BadRequest:
        await msg.edit_text(text)
