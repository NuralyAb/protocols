"""Silero VAD — voice activity detection. Used to trim silence before ASR."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class VadSegment:
    start_ms: int
    end_ms: int


def voice_segments(wav_path: str | Path, min_silence_ms: int = 500) -> list[VadSegment]:
    import torch
    from silero_vad import get_speech_timestamps, load_silero_vad, read_audio

    model = load_silero_vad()
    wav = read_audio(str(wav_path), sampling_rate=16000)
    ts = get_speech_timestamps(
        wav,
        model,
        sampling_rate=16000,
        min_silence_duration_ms=min_silence_ms,
        return_seconds=False,
    )
    segs: list[VadSegment] = []
    for t in ts:
        start_ms = int(t["start"] / 16000 * 1000)
        end_ms = int(t["end"] / 16000 * 1000)
        segs.append(VadSegment(start_ms=start_ms, end_ms=end_ms))
    _ = torch  # silence unused import warning
    return segs
