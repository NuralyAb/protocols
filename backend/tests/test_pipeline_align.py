"""Unit tests for speaker-alignment and segment-merge logic (no ML deps)."""
from app.services.asr.whisper_service import WhisperSegment
from app.services.diarization.pyannote_service import DiarizationTurn
from app.services.pipeline.offline import Segment, _assign_speaker, _merge_same_speaker


def test_assign_speaker_picks_max_overlap() -> None:
    turns = [
        DiarizationTurn(start_ms=0, end_ms=2000, speaker="SPEAKER_00"),
        DiarizationTurn(start_ms=2000, end_ms=5000, speaker="SPEAKER_01"),
    ]
    seg = WhisperSegment(start_ms=1500, end_ms=4500, text="hi", language="ru",
                          avg_logprob=-0.1, no_speech_prob=0.0)
    # 500ms overlap with SPEAKER_00 vs 2500ms with SPEAKER_01
    assert _assign_speaker(seg, turns) == "SPEAKER_01"


def test_merge_same_speaker_within_gap() -> None:
    segs = [
        Segment("SPEAKER_00", "kk", 0, 1000, "Сәлем", 0.9),
        Segment("SPEAKER_00", "kk", 1300, 2200, "әлем", 0.85),
        Segment("SPEAKER_01", "kk", 2300, 3000, "рақмет", 0.8),
    ]
    merged = _merge_same_speaker(segs, gap_ms=500)
    assert len(merged) == 2
    assert merged[0].text == "Сәлем әлем"
    assert merged[0].end_time == 2200
    assert merged[1].speaker == "SPEAKER_01"


def test_merge_respects_language_boundary() -> None:
    segs = [
        Segment("SPEAKER_00", "kk", 0, 1000, "Сәлем", 0.9),
        Segment("SPEAKER_00", "ru", 1100, 2000, "Привет", 0.9),
    ]
    merged = _merge_same_speaker(segs, gap_ms=500)
    assert len(merged) == 2


def test_confidence_bounds() -> None:
    s = WhisperSegment(start_ms=0, end_ms=100, text="x", language="en",
                       avg_logprob=-0.5, no_speech_prob=0.1)
    assert 0.0 <= s.confidence <= 1.0
