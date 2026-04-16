"""Offline audio → protocol pipeline.

Runs inside the asr-worker Celery container (has torch / faster-whisper / pyannote).
"""
from __future__ import annotations

import tempfile
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.asr.whisper_service import WhisperSegment, transcribe_file
from app.services.diarization.pyannote_service import DiarizationTurn, diarize
from app.services.preprocessing.normalize import probe_duration_ms, to_wav_16k_mono
from app.services.storage.s3_service import sync_download_to

log = get_logger("pipeline.offline")


@dataclass(slots=True)
class Segment:
    speaker: str
    language: str | None
    start_time: int
    end_time: int
    text: str
    confidence: float | None


def _assign_speaker(asr_seg: WhisperSegment, turns: list[DiarizationTurn]) -> str:
    """Pick the diarization turn with maximum temporal overlap."""
    best: tuple[int, str] = (-1, "SPEAKER_00")
    for t in turns:
        overlap = max(0, min(asr_seg.end_ms, t.end_ms) - max(asr_seg.start_ms, t.start_ms))
        if overlap > best[0]:
            best = (overlap, t.speaker)
    return best[1]


def _merge_same_speaker(segments: list[Segment], gap_ms: int = 500) -> list[Segment]:
    if not segments:
        return segments
    segments.sort(key=lambda s: s.start_time)
    out: list[Segment] = [segments[0]]
    for s in segments[1:]:
        prev = out[-1]
        if (
            s.speaker == prev.speaker
            and s.language == prev.language
            and s.start_time - prev.end_time <= gap_ms
        ):
            out[-1] = Segment(
                speaker=prev.speaker,
                language=prev.language,
                start_time=prev.start_time,
                end_time=s.end_time,
                text=(prev.text + " " + s.text).strip(),
                confidence=(
                    min(prev.confidence, s.confidence)
                    if prev.confidence is not None and s.confidence is not None
                    else (prev.confidence or s.confidence)
                ),
            )
        else:
            out.append(s)
    return out


def run_offline_pipeline(
    *,
    source_bucket: str,
    source_key: str,
    languages_hint: list[str] | None = None,
    progress_cb=None,
) -> dict[str, Any]:
    settings = get_settings()

    def progress(p: int, stage: str) -> None:
        if progress_cb:
            progress_cb(p, stage)
        log.info("pipeline.progress", stage=stage, pct=p)

    with tempfile.TemporaryDirectory(prefix="protocol_") as tmp_root:
        tmp = Path(tmp_root)
        src = tmp / "source" / Path(source_key).name
        progress(5, "download")
        sync_download_to(source_bucket, source_key, str(src))

        progress(15, "normalize")
        wav = to_wav_16k_mono(src, tmp / "audio.wav", loudnorm=True)
        duration_ms = probe_duration_ms(wav)

        progress(30, "diarize")
        try:
            turns = diarize(wav)
        except Exception as e:  # noqa: BLE001
            log.warning("diarization.failed", error=str(e))
            turns = [DiarizationTurn(start_ms=0, end_ms=duration_ms, speaker="SPEAKER_00")]

        progress(55, "asr")
        force_lang = languages_hint[0] if languages_hint and len(languages_hint) == 1 else None
        if settings.asr_provider == "openai" and settings.openai_api_key:
            from app.services.asr.openai_asr import transcribe_file_openai

            raw = transcribe_file_openai(wav, language=force_lang)
            asr_segments = [
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
            asr_model_label = settings.openai_asr_model
        else:
            asr_segments = transcribe_file(
                wav,
                language=force_lang,
                languages_hint=languages_hint,
                vad_filter=True,
            )
            asr_model_label = settings.asr_model

        progress(85, "align")
        joined: list[Segment] = []
        for seg in asr_segments:
            if not seg.text:
                continue
            spk = _assign_speaker(seg, turns)
            joined.append(
                Segment(
                    speaker=spk,
                    language=seg.language,
                    start_time=seg.start_ms,
                    end_time=seg.end_ms,
                    text=seg.text,
                    confidence=seg.confidence,
                )
            )
        merged = _merge_same_speaker(joined, gap_ms=500)

        diar_ids = sorted({t.speaker for t in turns})
        participants = [
            {
                "id": did,
                "label": f"Участник {i + 1}",
                "role": None,
            }
            for i, did in enumerate(diar_ids)
        ]

        lang_counter: Counter[str] = Counter(s.language for s in merged if s.language)
        languages_detected = [lang for lang, _ in lang_counter.most_common()]

        result = {
            "transcript": [
                {
                    "speaker": s.speaker,
                    "role": None,
                    "language": s.language,
                    "input_modality": "speech",
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "text": s.text,
                    "confidence": s.confidence,
                }
                for s in merged
            ],
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
                "duration_ms": duration_ms,
                "languages_detected": languages_detected,
                "model_versions": {
                    "asr": asr_model_label,
                    "asr_provider": settings.asr_provider,
                    "diarization": settings.diarization_model,
                    "pipeline": "offline@v1",
                },
            },
        }

        progress(92, "summarize")
        try:
            from app.services.summarization.llm_service import merge_into_result, summarize

            draft = summarize(result["transcript"], languages_detected=languages_detected)
            merge_into_result(result, draft)
        except Exception as e:  # noqa: BLE001
            # Summarization is best-effort — a failure shouldn't lose the transcript.
            log.warning("summarization.failed", error=str(e))
            result.setdefault("metadata", {})["summarization_error"] = str(e)[:500]

        progress(100, "done")
        return {"result": result, "duration_ms": duration_ms, "segments": [asdict(s) for s in merged], "turns": [asdict(t) for t in turns]}
