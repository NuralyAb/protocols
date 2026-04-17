# ── Monkey-patch for gradio_client schema bug ────────────────────────────
import gradio_client.utils as _gu
_orig_jst = _gu._json_schema_to_python_type
def _safe_jst(schema, defs=None):
    if isinstance(schema, bool):
        return "Any"
    if isinstance(schema, dict) and "additionalProperties" in schema:
        ap = schema["additionalProperties"]
        if isinstance(ap, bool):
            schema = {k: v for k, v in schema.items() if k != "additionalProperties"}
    return _orig_jst(schema, defs)
_gu._json_schema_to_python_type = _safe_jst
_orig_gt = _gu.get_type
def _safe_gt(schema):
    if isinstance(schema, bool):
        return "Any"
    return _orig_gt(schema)
_gu.get_type = _safe_gt
# ── End patch ────────────────────────────────────────────────────────────

import json
import os
import wave
import spaces
import torch
import gradio as gr
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

MODEL_ID = "Uali/whisper-turbo-ksc2-kazakh-finetuned"

print(f"Loading {MODEL_ID} on CPU...")
processor = AutoProcessor.from_pretrained(MODEL_ID)
model = AutoModelForSpeechSeq2Seq.from_pretrained(
    MODEL_ID, torch_dtype=torch.float16, low_cpu_mem_usage=True,
)
pipe = pipeline(
    "automatic-speech-recognition",
    model=model, tokenizer=processor.tokenizer,
    feature_extractor=processor.feature_extractor,
    torch_dtype=torch.float16, device="cpu",
)
print("Model loaded on CPU, ready for inference.")


# ── Anti-loop generate_kwargs for Whisper ────────────────────────────────
# Whisper is infamous for degenerating into "word word word word..." on silence
# or low-confidence chunks. These settings, in order of impact:
#   - condition_on_prev_tokens=False  → biggest win; stops cross-chunk loops
#   - no_repeat_ngram_size=3          → forbids 3-gram repetition
#   - compression_ratio_threshold     → retries with higher temperature if
#                                       output compresses too well (= repetition)
#   - logprob_threshold               → retries if avg logprob is too low
#   - no_speech_threshold             → drops the segment entirely as silence
#   - temperature tuple               → fallback schedule for the retries above
GEN_KWARGS = {
    "task": "transcribe",
    "condition_on_prev_tokens": False,
    "no_repeat_ngram_size": 3,
    "repetition_penalty": 1.2,
    "compression_ratio_threshold": 2.4,
    "logprob_threshold": -1.0,
    "no_speech_threshold": 0.6,
    "temperature": (0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
}


def _wav_duration_s(path: str) -> float:
    try:
        with wave.open(path, "rb") as w:
            frames = w.getnframes()
            rate = w.getframerate() or 16000
            return frames / float(rate)
    except Exception:
        return 0.0


@spaces.GPU(duration=60)
def transcribe(audio_path, language):
    if not audio_path:
        return json.dumps({"text": "", "chunks": []}, ensure_ascii=False)

    # Very short audio → skip; Whisper loops on <~0.4s.
    dur = _wav_duration_s(audio_path)
    if dur and dur < 0.4:
        return json.dumps({"text": "", "chunks": [], "skipped": "too_short", "duration_s": dur},
                          ensure_ascii=False)

    pipe.model.to("cuda")
    pipe.device = torch.device("cuda")
    try:
        result = pipe(
            audio_path,
            generate_kwargs={**GEN_KWARGS, "language": language or "kk"},
            return_timestamps=True,
            chunk_length_s=30,
            batch_size=8,
        )
    finally:
        pipe.model.to("cpu")
        pipe.device = torch.device("cpu")
        torch.cuda.empty_cache()

    # Extra safety: strip obvious repetition loops post-hoc.
    text = (result.get("text") or "").strip()
    if text:
        text = _collapse_repeats(text)
        result["text"] = text
    chunks = result.get("chunks") or []
    for c in chunks:
        if c.get("text"):
            c["text"] = _collapse_repeats(c["text"].strip())
    return json.dumps(result, ensure_ascii=False, indent=2)


def _collapse_repeats(text: str) -> str:
    """Collapse degenerate word-level repetitions (e.g. 'көп көп көп ...' → 'көп')."""
    words = text.split()
    if len(words) < 6:
        return text
    out = [words[0]]
    streak = 1
    for w in words[1:]:
        if w == out[-1]:
            streak += 1
            if streak <= 2:
                out.append(w)
        else:
            streak = 1
            out.append(w)
    # Also collapse repeated bigrams ("өмірі өмірі өмірі ...")
    final = []
    i = 0
    while i < len(out):
        if (
            i + 3 < len(out)
            and out[i] == out[i + 2]
            and out[i + 1] == out[i + 3]
        ):
            final.extend([out[i], out[i + 1]])
            j = i + 4
            while (
                j + 1 < len(out)
                and out[j] == out[i]
                and out[j + 1] == out[i + 1]
            ):
                j += 2
            i = j
        else:
            final.append(out[i])
            i += 1
    return " ".join(final)


demo = gr.Interface(
    fn=transcribe,
    inputs=[
        gr.Audio(type="filepath", label="Audio"),
        gr.Dropdown(choices=["kk", "ru", "en"], value="kk", label="Language"),
    ],
    outputs=gr.Textbox(label="Result", lines=10),
    title="Kazakh ASR",
    description="Whisper fine-tuned for Kazakh on ZeroGPU A100 (with anti-loop guards)",
)

demo.launch(show_error=True)
