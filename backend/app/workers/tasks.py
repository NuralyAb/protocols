"""Celery tasks for ASR workers."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import Job, JobStatus, Speaker, TranscriptSegment
from app.db.sync_session import SyncSessionLocal
from app.workers.celery_app import celery_app

log = get_logger("worker.tasks")


@celery_app.task(name="app.workers.tasks.process_audio", bind=True, max_retries=1)
def process_audio(self, job_id: str) -> dict[str, Any]:
    """Offline pipeline: download → normalize → diarize → ASR → align → persist."""
    from app.services.pipeline.offline import run_offline_pipeline  # lazy import (heavy)

    settings = get_settings()
    job_uuid = uuid.UUID(job_id)

    with SyncSessionLocal() as db:
        job = db.scalar(select(Job).where(Job.id == job_uuid))
        if not job:
            log.error("job.missing", job_id=job_id)
            return {"status": "missing"}
        if not job.source_key:
            job.status = JobStatus.failed
            job.error = "source_key is empty"
            db.commit()
            return {"status": "failed", "reason": "no_source"}

        job.status = JobStatus.processing
        job.progress = 1
        db.commit()

        def _progress(pct: int, stage: str) -> None:
            with SyncSessionLocal() as s2:
                j = s2.get(Job, job_uuid)
                if j:
                    j.progress = pct
                    s2.commit()
            self.update_state(state="PROGRESS", meta={"pct": pct, "stage": stage})

        try:
            out = run_offline_pipeline(
                source_bucket=settings.s3_bucket_media,
                source_key=job.source_key,
                languages_hint=job.languages_hint,
                progress_cb=_progress,
            )
        except Exception as e:  # noqa: BLE001
            log.exception("pipeline.failed", job_id=job_id)
            job2 = db.get(Job, job_uuid)
            if job2:
                job2.status = JobStatus.failed
                job2.error = str(e)[:2000]
                job2.progress = 0
                db.commit()
            raise

        job = db.get(Job, job_uuid)
        if not job:
            return {"status": "missing_after"}

        job.result = out["result"]
        job.duration_ms = out["duration_ms"]
        job.model_versions = out["result"]["metadata"]["model_versions"]
        job.status = JobStatus.completed
        job.progress = 100

        # Persist speakers
        existing_speakers = {
            s.diarization_id: s
            for s in db.scalars(select(Speaker).where(Speaker.job_id == job_uuid)).all()
        }
        participants = out["result"]["protocol"]["participants"]
        for p in participants:
            did = p["id"]
            if did in existing_speakers:
                continue
            db.add(Speaker(job_id=job_uuid, diarization_id=did, label=p["label"]))

        # Persist transcript rows (append-only; wipe prior if re-run)
        db.query(TranscriptSegment).filter(TranscriptSegment.job_id == job_uuid).delete()
        for seg in out["segments"]:
            db.add(
                TranscriptSegment(
                    job_id=job_uuid,
                    speaker_diarization_id=seg["speaker"],
                    language=seg["language"],
                    start_ms=seg["start_time"],
                    end_ms=seg["end_time"],
                    text=seg["text"],
                    confidence=seg["confidence"],
                )
            )
        db.commit()
        log.info("job.completed", job_id=job_id, duration_ms=out["duration_ms"], segments=len(out["segments"]))
        return {"status": "completed", "segments": len(out["segments"])}


@celery_app.task(name="app.workers.tasks.transcribe_utterance", bind=True, max_retries=1)
def transcribe_utterance(
    self,
    session_id: str,
    user_id: str,
    wav_b64: str,
    start_ms: int,
    end_ms: int,
    language: str | None,
    prefer_kazakh: bool = False,
    use_hf: bool = False,
    use_space: bool = False,
    use_openai_transcribe: bool = False,
) -> dict[str, Any]:
    """Decode one utterance → Whisper → persist TranscriptSegment → publish WS event."""
    import base64
    import json
    import tempfile

    import redis as redis_lib

    from app.services.asr.whisper_service import transcribe_file
    from app.db.models import TranscriptSegment

    settings = get_settings()

    wav_bytes = base64.b64decode(wav_b64)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(wav_bytes)
        tmp_path = tmp.name

    try:
        if use_openai_transcribe:
            from app.services.asr.openai_asr import transcribe_file_openai
            from app.services.asr.whisper_service import WhisperSegment

            raw = transcribe_file_openai(tmp_path, language=language)
            segs = [
                WhisperSegment(
                    start_ms=s.start_ms,
                    end_ms=s.end_ms,
                    text=s.text,
                    language=s.language,
                    avg_logprob=s.avg_logprob,
                    no_speech_prob=s.no_speech_prob,
                )
                for s in raw
            ]
        elif use_space:
            from app.services.asr.hf_space import transcribe_file_space
            from app.services.asr.whisper_service import WhisperSegment

            raw = transcribe_file_space(tmp_path, language=language or "kk")
            segs = [
                WhisperSegment(
                    start_ms=s.start_ms,
                    end_ms=s.end_ms,
                    text=s.text,
                    language=s.language,
                    avg_logprob=s.avg_logprob,
                    no_speech_prob=s.no_speech_prob,
                )
                for s in raw
            ]
        elif use_hf:
            from app.services.asr.hf_inference import transcribe_file_hf
            from app.services.asr.whisper_service import WhisperSegment

            raw = transcribe_file_hf(tmp_path, language=language or "kk")
            segs = [
                WhisperSegment(
                    start_ms=s.start_ms,
                    end_ms=s.end_ms,
                    text=s.text,
                    language=s.language,
                    avg_logprob=s.avg_logprob,
                    no_speech_prob=s.no_speech_prob,
                )
                for s in raw
            ]
        else:
            segs = transcribe_file(
                tmp_path,
                language=language,
                vad_filter=True,
                use_prompt=False,
                prefer_kazakh=prefer_kazakh,
            )
    except Exception as e:  # noqa: BLE001
        log.exception("utterance.asr_failed", sid=session_id)
        _publish(settings, session_id, {"type": "error", "message": str(e)[:200]})
        return {"status": "failed"}
    finally:
        try:
            import os

            os.unlink(tmp_path)
        except OSError:
            pass

    text = " ".join(s.text for s in segs).strip()
    if not text:
        return {"status": "empty"}

    detected_lang = segs[0].language if segs else (language or "unknown")
    confidence = segs[0].confidence if segs else None

    sess_uuid = uuid.UUID(session_id)
    with SyncSessionLocal() as db:
        db.add(
            TranscriptSegment(
                session_id=sess_uuid,
                speaker_diarization_id="SPEAKER_00",  # live: single-speaker default, edited later
                language=detected_lang,
                start_ms=start_ms,
                end_ms=end_ms,
                text=text,
                confidence=confidence,
            )
        )
        db.commit()

    _publish(
        settings,
        session_id,
        {
            "type": "final",
            "start_ms": start_ms,
            "end_ms": end_ms,
            "speaker": "SPEAKER_00",
            "language": detected_lang,
            "text": text,
            "confidence": confidence,
        },
    )
    return {"status": "ok", "chars": len(text)}


def _publish(settings, session_id: str, event: dict[str, Any]) -> None:
    import json as _json

    import redis as _redis

    r = _redis.from_url(settings.redis_url)
    try:
        r.publish(f"session:{session_id}", _json.dumps(event))
    finally:
        try:
            r.close()
        except Exception:  # noqa: BLE001
            pass


