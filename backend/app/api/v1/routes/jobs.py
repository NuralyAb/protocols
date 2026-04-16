from typing import Literal
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Request, Response, UploadFile, status
from sqlalchemy import select

from app.api.v1.deps import CurrentUser, DBSession
from app.api.v1.schemas import JobCreateResponse, JobOut, JobStatusOut, SpeakerPatch
from app.core.config import get_settings
from app.core.limiter import limiter
from app.db.models import Export, ExportFormat, Job, JobStatus, Speaker
from app.services.export import render as render_export
from app.services.storage.s3_service import export_key, media_key, upload_fileobj

router = APIRouter()

ALLOWED_AUDIO_TYPES = {
    "audio/wav", "audio/x-wav",
    "audio/mpeg", "audio/mp3",
    "audio/mp4", "audio/m4a", "audio/x-m4a",
    "audio/ogg", "audio/flac",
    "audio/webm", "video/webm",
    "application/octet-stream",
}
ALLOWED_EXT = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm"}
MAX_UPLOAD_BYTES = 500 * 1024 * 1024  # 500MB


def _ext_ok(filename: str | None) -> bool:
    if not filename:
        return False
    dot = filename.rfind(".")
    return dot != -1 and filename[dot:].lower() in ALLOWED_EXT


AUDIO_MAGIC = (
    b"RIFF",           # WAV
    b"ID3",            # MP3 with ID3
    b"\xff\xfb",       # MP3 raw
    b"\xff\xf3",       # MP3 raw
    b"\xff\xf2",       # MP3 raw
    b"OggS",           # Ogg
    b"fLaC",           # FLAC
    b"\x1a\x45\xdf\xa3",  # Matroska / WebM
)


def _looks_like_audio(prefix: bytes, filename: str | None) -> bool:
    """Fallback magic-byte sniff. Accepts MP4/M4A containers via 'ftyp' at offset 4."""
    if any(prefix.startswith(m) for m in AUDIO_MAGIC):
        return True
    if len(prefix) >= 12 and prefix[4:8] == b"ftyp":  # MP4/M4A
        return True
    # Best-effort: rely on extension if header sniff fails (encrypted etc.)
    return _ext_ok(filename)


@router.post("/build_protocol", response_model=JobCreateResponse, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("20/hour")
async def build_protocol(
    request: Request,
    user: CurrentUser,
    db: DBSession,
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    languages: str | None = Form(default="kk,ru,en"),
) -> JobCreateResponse:
    if not _ext_ok(file.filename) and (file.content_type not in ALLOWED_AUDIO_TYPES):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, f"Unsupported: {file.filename} / {file.content_type}")

    # Magic-byte sniff — 16 bytes is enough for all formats we accept.
    head = await file.read(16)
    if not _looks_like_audio(head, file.filename):
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "File does not look like a supported audio/video container",
        )
    await file.seek(0)

    settings = get_settings()
    key = media_key(str(user.id), file.filename or "audio.bin")
    await upload_fileobj(settings.s3_bucket_media, key, file.file, content_type=file.content_type)

    lang_hint = [x.strip() for x in (languages or "").split(",") if x.strip()] or None

    job = Job(
        owner_id=user.id,
        title=title or file.filename,
        source_key=key,
        source_filename=file.filename,
        languages_hint=lang_hint,
        status=JobStatus.pending,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Enqueue without importing heavy ML stack into the API container.
    from app.workers.celery_app import celery_app  # noqa: PLC0415

    celery_app.send_task("app.workers.tasks.process_audio", args=[str(job.id)], queue="asr")

    return JobCreateResponse(job_id=job.id, status=job.status)


@router.get("/jobs", response_model=list[JobOut])
async def list_jobs(user: CurrentUser, db: DBSession, limit: int = 50) -> list[Job]:
    rows = await db.scalars(
        select(Job)
        .where(Job.owner_id == user.id)
        .order_by(Job.created_at.desc())
        .limit(min(max(limit, 1), 200))
    )
    return list(rows.all())


@router.get("/jobs/{job_id}", response_model=JobStatusOut)
async def job_status_endpoint(job_id: UUID, user: CurrentUser, db: DBSession) -> Job:
    job = await db.scalar(select(Job).where(Job.id == job_id, Job.owner_id == user.id))
    if not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    return job


@router.get("/jobs/{job_id}/result", response_model=JobOut)
async def job_result(job_id: UUID, user: CurrentUser, db: DBSession) -> Job:
    job = await db.scalar(select(Job).where(Job.id == job_id, Job.owner_id == user.id))
    if not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    return job


@router.patch("/jobs/{job_id}/speakers", status_code=status.HTTP_204_NO_CONTENT)
async def patch_speakers(
    job_id: UUID,
    patches: list[SpeakerPatch],
    user: CurrentUser,
    db: DBSession,
) -> None:
    job = await db.scalar(select(Job).where(Job.id == job_id, Job.owner_id == user.id))
    if not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    for p in patches:
        sp = await db.scalar(
            select(Speaker).where(Speaker.job_id == job_id, Speaker.diarization_id == p.diarization_id)
        )
        if not sp:
            sp = Speaker(job_id=job_id, diarization_id=p.diarization_id, label=p.label or p.diarization_id)
            db.add(sp)
        if p.label is not None:
            sp.label = p.label
        if p.role is not None:
            sp.role = p.role
    await db.commit()


@router.get("/jobs/{job_id}/export")
async def export_job(
    job_id: UUID,
    user: CurrentUser,
    db: DBSession,
    format: Literal["json", "pdf", "docx", "txt", "srt", "vtt"] = "json",
) -> Response:
    job = await db.scalar(select(Job).where(Job.id == job_id, Job.owner_id == user.id))
    if not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")

    fmt = ExportFormat(format)
    result = job.result or {"transcript": [], "protocol": {}, "metadata": {}}
    try:
        body, content_type, ext = render_export(result, fmt)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Render failed: {e}") from e

    # Archive export in S3 (best-effort) + record in DB.
    settings = get_settings()
    key = export_key(str(job.id), ext)
    try:
        from io import BytesIO

        await upload_fileobj(settings.s3_bucket_exports, key, BytesIO(body), content_type=content_type)
        db.add(Export(job_id=job.id, format=fmt, s3_key=key, size_bytes=len(body)))
        await db.commit()
    except Exception:  # noqa: BLE001
        await db.rollback()

    safe_name = (job.title or f"protocol_{job.id}").replace('"', "").strip()
    return Response(
        content=body,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}.{ext}"',
            "Cache-Control": "no-store",
        },
    )
