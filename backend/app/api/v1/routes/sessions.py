from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.api.v1.deps import CurrentUser, DBSession
from app.api.v1.schemas import (
    LiveSessionCreate,
    LiveSessionOut,
    ProtocolGenerateRequest,
    TemplateOut,
)
from app.core.config import get_settings
from app.db.models import Export, ExportFormat, LiveSession, Speaker, TranscriptSegment
from app.services.export import render as render_export
from app.services.export.markdown_convert import markdown_to_docx, markdown_to_pdf
from app.services.storage.s3_service import export_key, upload_fileobj
from app.services.summarization.protocol_generator import generate_from_template
from app.services.summarization.templates import get_template, list_templates

router = APIRouter()


@router.get("/templates", response_model=list[TemplateOut])
async def list_protocol_templates(user: CurrentUser) -> list[TemplateOut]:
    _ = user  # auth-gated; list itself is user-agnostic
    return [
        TemplateOut(id=m.id, name=m.name, description=m.description, language=m.language)
        for m in list_templates()
    ]


@router.post("", response_model=LiveSessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(body: LiveSessionCreate, user: CurrentUser, db: DBSession) -> LiveSession:
    s = LiveSession(
        owner_id=user.id,
        title=body.title,
        languages=body.languages,
        asr_provider=body.asr_provider,
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
