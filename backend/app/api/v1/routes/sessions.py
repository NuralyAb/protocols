import secrets
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import select

from app.api.v1.deps import CurrentUser, DBSession
from app.api.v1.schemas import (
    LiveSessionCreate,
    LiveSessionOut,
    ProtocolGenerateRequest,
    PublicSessionOut,
    TemplateOut,
    ViewerTokenOut,
)
from app.core.config import get_settings
from app.db.models import Export, ExportFormat, LiveSession, Speaker, TranscriptSegment
from app.services.export import render as render_export
from app.services.export.markdown_convert import markdown_to_docx, markdown_to_pdf
from app.services.storage.s3_service import export_key, presign_get_url, upload_fileobj
from app.services.summarization.insights import build_insights
from app.services.summarization.protocol_generator import generate_from_template
from app.services.summarization.templates import (
    get_template,
    list_templates,
    save_custom_template,
)
from app.services.summarization.translator import SUPPORTED as TRANSLATE_LANGS, translate_batch

router = APIRouter()


@router.get("/templates", response_model=list[TemplateOut])
async def list_protocol_templates(user: CurrentUser) -> list[TemplateOut]:
    _ = user  # auth-gated; list itself is user-agnostic
    return [
        TemplateOut(id=m.id, name=m.name, description=m.description, language=m.language)
        for m in list_templates()
    ]


_MAX_TEMPLATE_BYTES = 64 * 1024


@router.post("/templates", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
async def upload_protocol_template(
    user: CurrentUser,
    name: str = Form(..., min_length=1, max_length=120),
    description: str = Form("", max_length=500),
    language: str = Form("ru", max_length=8),
    file: UploadFile | None = File(None),
    body: str | None = Form(None),
) -> TemplateOut:
    _ = user
    raw: str
    if file is not None:
        blob = await file.read()
        if len(blob) > _MAX_TEMPLATE_BYTES:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Template too large")
        try:
            raw = blob.decode("utf-8")
        except UnicodeDecodeError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Template must be UTF-8 text") from e
    elif body is not None:
        raw = body
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Provide `file` or `body`")

    raw = raw.strip()
    if not raw:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Template body is empty")

    meta = save_custom_template(name=name, description=description, language=language, body=raw)
    return TemplateOut(id=meta.id, name=meta.name, description=meta.description, language=meta.language)


@router.get("", response_model=list[LiveSessionOut])
async def list_sessions(user: CurrentUser, db: DBSession, limit: int = 50) -> list[LiveSession]:
    limit = max(1, min(limit, 200))
    rows = await db.scalars(
        select(LiveSession)
        .where(LiveSession.owner_id == user.id)
        .order_by(LiveSession.started_at.desc())
        .limit(limit)
    )
    return list(rows.all())


def _gen_friendly_id_base(now: "datetime | None" = None) -> str:
    """`DDMMYYYY-HHMM` in Asia/Almaty (UTC+5)."""
    from datetime import datetime, timezone
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("Asia/Almaty")
    except Exception:  # pragma: no cover
        tz = timezone.utc
    n = (now or datetime.now(tz=timezone.utc)).astimezone(tz)
    return f"{n.day:02d}{n.month:02d}{n.year:04d}-{n.hour:02d}{n.minute:02d}"


async def _allocate_friendly_id(db) -> str:
    base = _gen_friendly_id_base()
    candidate = base
    suffix = 1
    while True:
        exists = await db.scalar(
            select(LiveSession.id).where(LiveSession.friendly_id == candidate)
        )
        if not exists:
            return candidate
        suffix += 1
        candidate = f"{base}-{suffix}"
        if suffix > 99:  # absurd, but guard against runaway loop
            import secrets as _s
            return f"{base}-{_s.token_hex(2)}"


@router.post("", response_model=LiveSessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(body: LiveSessionCreate, user: CurrentUser, db: DBSession) -> LiveSession:
    fid = await _allocate_friendly_id(db)
    s = LiveSession(
        owner_id=user.id,
        title=body.title,
        languages=body.languages,
        asr_provider=body.asr_provider,
        friendly_id=fid,
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def _load_session(session_id: UUID, user, db) -> LiveSession:
    s = await db.scalar(
        select(LiveSession).where(LiveSession.id == session_id, LiveSession.owner_id == user.id)
    )
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    return s


@router.get("/{session_id}", response_model=LiveSessionOut)
async def get_session(session_id: UUID, user: CurrentUser, db: DBSession) -> LiveSession:
    return await _load_session(session_id, user, db)


async def _build_result(session_id: UUID, db) -> dict:
    rows = (
        await db.scalars(
            select(TranscriptSegment)
            .where(TranscriptSegment.session_id == session_id)
            .order_by(TranscriptSegment.start_ms)
        )
    ).all()
    speakers = (
        await db.scalars(select(Speaker).where(Speaker.session_id == session_id))
    ).all()
    speaker_by_id = {sp.diarization_id: sp for sp in speakers}
    diar_ids = sorted({r.speaker_diarization_id or "SPEAKER_00" for r in rows})
    participants = []
    for i, did in enumerate(diar_ids):
        sp = speaker_by_id.get(did)
        participants.append(
            {
                "id": did,
                "label": (sp.label if sp else None) or f"Участник {i + 1}",
                "role": sp.role if sp else None,
            }
        )

    transcript = [
        {
            "speaker": r.speaker_diarization_id or "SPEAKER_00",
            "role": None,
            "language": r.language,
            "input_modality": r.input_modality.value if r.input_modality else "speech",
            "start_time": r.start_ms,
            "end_time": r.end_ms,
            "text": r.text,
            "confidence": r.confidence,
        }
        for r in rows
    ]

    languages = sorted({r.language for r in rows if r.language})
    last_end = rows[-1].end_ms if rows else 0
    return {
        "transcript": transcript,
        "protocol": {
            "title": None,
            "date": None,
            "participants": participants,
            "agenda": [],
            "discussion": [],
            "decisions": [],
            "action_items": [],
        },
        "metadata": {
            "duration_ms": last_end,
            "languages_detected": languages,
            "model_versions": {"pipeline": "live@v1"},
        },
    }


@router.get("/{session_id}/snapshot")
async def session_snapshot(session_id: UUID, user: CurrentUser, db: DBSession) -> dict:
    await _load_session(session_id, user, db)
    return await _build_result(session_id, db)


@router.get("/{session_id}/translate")
async def translate_session_transcript(
    session_id: UUID,
    user: CurrentUser,
    db: DBSession,
    lang: Literal["ru", "kk", "en"] = Query(..., description="Target language"),
) -> dict:
    """Translate the transcript to a target language. Cached per-segment in DB."""
    await _load_session(session_id, user, db)
    rows = (
        await db.scalars(
            select(TranscriptSegment)
            .where(TranscriptSegment.session_id == session_id)
            .order_by(TranscriptSegment.start_ms)
        )
    ).all()
    if not rows:
        return {"lang": lang, "segments": [], "cached": 0, "translated": 0}

    # Pass 1: collect what's missing.
    out_text: list[str] = [""] * len(rows)
    missing_indices: list[int] = []
    missing_texts: list[str] = []
    for i, r in enumerate(rows):
        cached = (r.translations or {}).get(lang)
        if isinstance(cached, str):
            out_text[i] = cached
            continue
        orig = (r.text or "").strip()
        if not orig:
            out_text[i] = ""
            continue
        missing_indices.append(i)
        missing_texts.append(orig)

    # Pass 2: translate missing + persist.
    if missing_texts:
        try:
            translated = await _run_sync_translate(missing_texts, lang)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Translation failed: {e}") from e

        for slot, idx in enumerate(missing_indices):
            new_text = translated[slot] if slot < len(translated) else missing_texts[slot]
            out_text[idx] = new_text
            existing = dict(rows[idx].translations or {})
            existing[lang] = new_text
            rows[idx].translations = existing
        await db.commit()

    segments = [
        {
            "speaker": r.speaker_diarization_id or "SPEAKER_00",
            "language": lang,
            "start_time": r.start_ms,
            "end_time": r.end_ms,
            "text": out_text[i],
            "confidence": r.confidence,
        }
        for i, r in enumerate(rows)
    ]
    return {
        "lang": lang,
        "segments": segments,
        "cached": len(rows) - len(missing_texts),
        "translated": len(missing_texts),
    }


async def _run_sync_translate(texts: list[str], lang: str) -> list[str]:
    import asyncio

    return await asyncio.to_thread(translate_batch, texts, lang)


@router.get("/{session_id}/audio")
async def session_audio(session_id: UUID, user: CurrentUser, db: DBSession) -> dict:
    """Return presigned URLs for inline playback and download of the session recording."""
    session = await _load_session(session_id, user, db)
    if not session.audio_key:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recording not available")
    settings = get_settings()
    filename = f"session_{session.id}.wav"
    stream_url = presign_get_url(
        settings.s3_bucket_media,
        session.audio_key,
        expires_in=3600,
        filename=filename,
        content_type="audio/wav",
        disposition="inline",
    )
    download_url = presign_get_url(
        settings.s3_bucket_media,
        session.audio_key,
        expires_in=3600,
        filename=filename,
        content_type="audio/wav",
        disposition="attachment",
    )
    return {
        "url": stream_url,
        "download_url": download_url,
        "filename": filename,
        "content_type": "audio/wav",
    }


@router.get("/{session_id}/export")
async def session_export(
    session_id: UUID,
    user: CurrentUser,
    db: DBSession,
    format: Literal["json", "pdf", "docx", "txt", "srt", "vtt"] = "json",
) -> Response:
    session = await _load_session(session_id, user, db)
    result = await _build_result(session_id, db)

    fmt = ExportFormat(format)
    body, content_type, ext = render_export(result, fmt)

    settings = get_settings()
    key = export_key(str(session.id), ext)
    try:
        from io import BytesIO

        await upload_fileobj(settings.s3_bucket_exports, key, BytesIO(body), content_type=content_type)
        db.add(Export(session_id=session.id, format=fmt, s3_key=key, size_bytes=len(body)))
        await db.commit()
    except Exception:  # noqa: BLE001
        await db.rollback()

    safe = (session.title or f"session_{session.id}").replace('"', "").strip()
    return Response(
        content=body,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{safe}.{ext}"',
            "Cache-Control": "no-store",
        },
    )


@router.post("/{session_id}/protocol")
async def generate_session_protocol(
    session_id: UUID,
    body: ProtocolGenerateRequest,
    user: CurrentUser,
    db: DBSession,
) -> Response:
    import asyncio

    session = await _load_session(session_id, user, db)
    template = get_template(body.template_id)
    if not template:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Template '{body.template_id}' not found")

    result = await _build_result(session_id, db)
    transcript = result.get("transcript") or []
    if not transcript:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Transcript is empty")
    languages = result.get("metadata", {}).get("languages_detected") or None

    try:
        markdown = await asyncio.to_thread(
            generate_from_template, transcript, template, languages
        )
    except RuntimeError as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"LLM error: {e}") from e

    safe_title = (session.title or f"protocol_{session.id}").replace('"', "").strip()

    if body.format == "markdown":
        return Response(
            content=markdown.encode("utf-8"),
            media_type="text/markdown; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{safe_title}.md"',
                "Cache-Control": "no-store",
                "X-Template-Id": template.meta.id,
            },
        )

    if body.format == "docx":
        data = await asyncio.to_thread(markdown_to_docx, markdown, safe_title)
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="{safe_title}.docx"',
                "Cache-Control": "no-store",
                "X-Template-Id": template.meta.id,
            },
        )

    if body.format == "pdf":
        data = await asyncio.to_thread(markdown_to_pdf, markdown, safe_title)
        return Response(
            content=data,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{safe_title}.pdf"',
                "Cache-Control": "no-store",
                "X-Template-Id": template.meta.id,
            },
        )

    raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unsupported format: {body.format}")


@router.post(
    "/{session_id}/viewer_token",
    response_model=ViewerTokenOut,
    status_code=status.HTTP_201_CREATED,
)
async def mint_viewer_token(
    session_id: UUID,
    user: CurrentUser,
    db: DBSession,
    rotate: bool = False,
) -> ViewerTokenOut:
    """Mint (or rotate) a read-only viewer token for the session.

    Anyone with the token can read the live transcript via the public WS and
    the public REST endpoints below. The token is opaque and bound to one session.
    """
    session = await _load_session(session_id, user, db)
    if rotate or not session.viewer_token:
        session.viewer_token = secrets.token_urlsafe(24)
        await db.commit()
        await db.refresh(session)
    return ViewerTokenOut(
        session_id=session.id,
        viewer_token=session.viewer_token or "",
        public_url_path=f"/public/session/{session.id}?token={session.viewer_token}",
    )


async def _load_public_session(session_id: UUID, token: str, db) -> LiveSession:
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing viewer token")
    s = await db.scalar(
        select(LiveSession).where(
            LiveSession.id == session_id,
            LiveSession.viewer_token == token,
        )
    )
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    return s


@router.get("/{session_id}/public", response_model=PublicSessionOut)
async def public_session_meta(
    session_id: UUID,
    db: DBSession,
    token: str = Query(..., description="Viewer token"),
) -> PublicSessionOut:
    s = await _load_public_session(session_id, token, db)
    return PublicSessionOut(
        id=s.id,
        title=s.title,
        is_active=s.is_active,
        languages=s.languages,
        started_at=s.started_at,
        ended_at=s.ended_at,
    )


@router.get("/{session_id}/public/transcript")
async def public_session_transcript(
    session_id: UUID,
    db: DBSession,
    token: str = Query(...),
) -> dict:
    """Snapshot of the public-readable transcript. Polling fallback if WS isn't usable."""
    await _load_public_session(session_id, token, db)
    return await _build_result(session_id, db)


@router.get("/by_friendly_id/{friendly_id}", response_model=LiveSessionOut)
async def session_by_friendly_id(
    friendly_id: str, user: CurrentUser, db: DBSession
) -> LiveSession:
    """Resolve a short DDMMYYYY-HHMM code (used by the Telegram bot) to the full session."""
    s = await db.scalar(
        select(LiveSession).where(
            LiveSession.friendly_id == friendly_id,
            LiveSession.owner_id == user.id,
        )
    )
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    return s


@router.get("/{session_id}/qa")
async def session_qa(
    session_id: UUID,
    user: CurrentUser,
    db: DBSession,
    question: str = Query(..., min_length=1, max_length=2000),
    lang: Literal["ru", "kk", "en"] | None = Query(None),
    k: int = Query(6, ge=1, le=20),
) -> dict:
    """Answer a free-form question about the session transcript via RAG."""
    import asyncio

    from app.services.qa import answer as qa_answer, pick_lang

    await _load_session(session_id, user, db)
    result = await _build_result(session_id, db)
    transcript = result.get("transcript") or []
    if not transcript:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transcript is empty")

    languages = result.get("metadata", {}).get("languages_detected") or None
    resolved_lang = pick_lang(lang, languages)
    return await asyncio.to_thread(
        qa_answer,
        str(session_id),
        transcript,
        question,
        lang=resolved_lang,
        k=k,
    )


@router.get("/{session_id}/insights")
async def session_insights(
    session_id: UUID,
    user: CurrentUser,
    db: DBSession,
    key_moments: bool = True,
) -> dict:
    """Speaker time, top words, and (optional) LLM-extracted key moments."""
    import asyncio

    await _load_session(session_id, user, db)
    result = await _build_result(session_id, db)
    transcript = result.get("transcript") or []
    participants = result.get("protocol", {}).get("participants") or []
    languages = result.get("metadata", {}).get("languages_detected") or None
    return await asyncio.to_thread(
        build_insights, transcript, participants, languages, include_key_moments=key_moments
    )


@router.patch("/{session_id}/speakers", status_code=status.HTTP_204_NO_CONTENT)
async def patch_session_speakers(
    session_id: UUID,
    patches: list[dict],
    user: CurrentUser,
    db: DBSession,
) -> None:
    await _load_session(session_id, user, db)
    for p in patches:
        did = p.get("diarization_id")
        if not did:
            continue
        sp = await db.scalar(
            select(Speaker).where(Speaker.session_id == session_id, Speaker.diarization_id == did)
        )
        if not sp:
            sp = Speaker(session_id=session_id, diarization_id=did, label=p.get("label") or did)
            db.add(sp)
        for field in ("label", "role"):
            if field in p:
                setattr(sp, field, p[field])
    await db.commit()
