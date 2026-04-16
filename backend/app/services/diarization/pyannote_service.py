"""pyannote.audio 3.1 speaker diarization."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger("diarization.pyannote")


@dataclass(slots=True)
class DiarizationTurn:
    start_ms: int
    end_ms: int
    speaker: str  # e.g. "SPEAKER_00"


@lru_cache(maxsize=1)
def _get_pipeline():
    import torch
    from pyannote.audio import Pipeline

    s = get_settings()
    if not s.huggingface_token:
        raise RuntimeError(
            "HUGGINGFACE_TOKEN required to download pyannote/speaker-diarization-3.1"
        )
    log.info("pyannote.load", model=s.diarization_model, device=s.asr_device)
    pipe = Pipeline.from_pretrained(s.diarization_model, use_auth_token=s.huggingface_token)
    if s.asr_device == "cuda" and torch.cuda.is_available():
        pipe.to(torch.device("cuda"))
    return pipe


def diarize(
    wav_path: str | Path,
    num_speakers: int | None = None,
    min_speakers: int | None = None,
    max_speakers: int | None = None,
) -> list[DiarizationTurn]:
    pipe = _get_pipeline()
    kwargs: dict = {}
    if num_speakers is not None:
        kwargs["num_speakers"] = num_speakers
    if min_speakers is not None:
        kwargs["min_speakers"] = min_speakers
    if max_speakers is not None:
        kwargs["max_speakers"] = max_speakers

    diar = pipe(str(wav_path), **kwargs)

    turns: list[DiarizationTurn] = []
    for turn, _, speaker in diar.itertracks(yield_label=True):
        turns.append(
            DiarizationTurn(
                start_ms=int(turn.start * 1000),
                end_ms=int(turn.end * 1000),
                speaker=str(speaker),
            )
        )
    turns.sort(key=lambda t: t.start_ms)
    return _merge_adjacent(turns, gap_ms=300)


def _merge_adjacent(turns: list[DiarizationTurn], gap_ms: int = 300) -> list[DiarizationTurn]:
    if not turns:
        return turns
    merged: list[DiarizationTurn] = [turns[0]]
    for t in turns[1:]:
        last = merged[-1]
        if t.speaker == last.speaker and t.start_ms - last.end_ms <= gap_ms:
            merged[-1] = DiarizationTurn(last.start_ms, max(last.end_ms, t.end_ms), last.speaker)
        else:
            merged.append(t)
    return merged
