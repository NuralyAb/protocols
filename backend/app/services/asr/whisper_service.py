"""faster-whisper wrapper with multi-model registry.

We keep at most ONE WhisperModel resident in VRAM (RTX 3050 = 4 GB).
Switching models triggers eviction + ``torch.cuda.empty_cache``.

Supports:
  - Vanilla CT2 repos (e.g. ``Systran/faster-whisper-large-v3``)
  - HuggingFace PyTorch repos (e.g. ``issai/whisper-large-v3-kazakh``) —
    auto-converted to CT2 format on first use, cached in /ml-models/asr/ct2/.
"""
from __future__ import annotations

import gc
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.asr.kazakh_glossary import prompt_for

log = get_logger("asr.whisper")

CT2_CACHE = Path("/ml-models/asr/ct2")


@dataclass(slots=True)
class WhisperSegment:
    start_ms: int
    end_ms: int
    text: str
    language: str
    avg_logprob: float
    no_speech_prob: float

    @property
    def confidence(self) -> float:
        base = max(0.0, min(1.0, 1.0 + self.avg_logprob))
        return round(base * (1.0 - min(1.0, self.no_speech_prob)), 3)


# Single-slot registry. Workers run with concurrency=1, no locking needed.
_loaded: dict | None = None


def _ensure_ct2(hf_repo: str) -> Path:
    """Convert a HF PyTorch Whisper checkpoint to CT2 once, cache forever."""
    target = CT2_CACHE / hf_repo.replace("/", "__")
    if (target / "model.bin").exists():
        return target
    log.info("ct2.convert.start", repo=hf_repo, target=str(target))
    target.parent.mkdir(parents=True, exist_ok=True)

    from ctranslate2.converters.transformers import TransformersConverter

    converter = TransformersConverter(
        model_name_or_path=hf_repo,
        copy_files=[
            "tokenizer.json",
            "preprocessor_config.json",
            "tokenizer_config.json",
            "special_tokens_map.json",
            "generation_config.json",
        ],
        load_as_float16=True,
    )
    converter.convert(output_dir=str(target), quantization="int8_float16", force=True)
    log.info("ct2.convert.done", target=str(target))
    return target


_CT2_NATIVE_PREFIXES = ("Systran/", "guillaumekln/", "deepdml/")


def _resolve_model_path(model_id: str) -> str:
    """CT2-native repos (faster-whisper-*) load directly; everything else (PyTorch
    HF Whisper checkpoints) is auto-converted to CT2 once."""
    # Bare names like "large-v3" are the canonical Systran repo names
    if "/" not in model_id:
        return model_id
    if any(model_id.startswith(p) for p in _CT2_NATIVE_PREFIXES):
        return model_id
    return str(_ensure_ct2(model_id))


def _evict() -> None:
    global _loaded
    if not _loaded:
        return
    log.info("whisper.evict", id=_loaded["id"])
    _loaded["model"] = None
    _loaded = None
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:  # noqa: BLE001
        pass


def _get_model_for(model_id: str):
    """Return a cached WhisperModel for ``model_id``, evicting any other model first."""
    global _loaded
    if _loaded and _loaded["id"] == model_id and _loaded.get("model") is not None:
        return _loaded["model"]

    _evict()

    from faster_whisper import WhisperModel

    s = get_settings()
    resolved = _resolve_model_path(model_id)
    log.info("whisper.load", id=model_id, resolved=resolved, device=s.asr_device, compute=s.asr_compute_type)
    model = WhisperModel(
        resolved,
        device=s.asr_device,
        compute_type=s.asr_compute_type,
        download_root="/ml-models/asr",
    )
    _loaded = {"id": model_id, "model": model}
    return model


def _pick_model_id(language: str | None, prefer_kazakh: bool) -> str:
    """Choose the best model for the requested language."""
    s = get_settings()
    if prefer_kazakh and (language is None or language == "kk"):
        return s.asr_kazakh_model  # e.g. issai/whisper-large-v3-kazakh
    return s.asr_model  # e.g. large-v3


def transcribe_file(
    wav_path: str | Path,
    language: str | None = None,
    languages_hint: list[str] | None = None,
    vad_filter: bool = True,
    use_prompt: bool = True,
    prefer_kazakh: bool = False,
) -> list[WhisperSegment]:
    """Run full-file transcription on the most appropriate model."""
    model_id = _pick_model_id(language, prefer_kazakh)
    model = _get_model_for(model_id)
    hint_lang = language or (languages_hint[0] if languages_hint else None)

    segments_iter, info = model.transcribe(
        str(wav_path),
        language=language,
        task="transcribe",
        vad_filter=vad_filter,
        vad_parameters={"min_silence_duration_ms": 500},
        condition_on_previous_text=False,
        initial_prompt=prompt_for(hint_lang) if use_prompt else None,
        beam_size=5,
        temperature=[0.0, 0.2, 0.4],
        word_timestamps=False,
    )

    detected = language or getattr(info, "language", None)

    out: list[WhisperSegment] = []
    for seg in segments_iter:
        out.append(
            WhisperSegment(
                start_ms=int(seg.start * 1000),
                end_ms=int(seg.end * 1000),
                text=seg.text.strip(),
                language=detected or "unknown",
                avg_logprob=float(seg.avg_logprob) if seg.avg_logprob is not None else -1.0,
                no_speech_prob=float(seg.no_speech_prob) if seg.no_speech_prob is not None else 0.0,
            )
        )
    return out


def transcribe_clip(
    wav_path: str | Path,
    start_ms: int,
    end_ms: int,
    language: str | None = None,
    prefer_kazakh: bool = False,
) -> list[WhisperSegment]:
    """Transcribe a bounded window (used to realign ASR with diarization turns)."""
    import soundfile as sf

    data, sr = sf.read(str(wav_path))
    s0 = int(start_ms / 1000 * sr)
    s1 = int(end_ms / 1000 * sr)
    clip = data[s0:s1]
    if len(clip) == 0:
        return []
    tmp = Path(wav_path).with_suffix(f".clip_{start_ms}_{end_ms}.wav")
    sf.write(tmp, clip, sr)
    try:
        segs = transcribe_file(tmp, language=language, prefer_kazakh=prefer_kazakh)
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
    for s in segs:
        s.start_ms += start_ms
        s.end_ms += start_ms
    return segs
