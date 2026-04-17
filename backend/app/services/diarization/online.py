"""Lightweight online speaker clustering for live sessions.

No external ML deps — pure numpy. Computes a 32-dim log-mel "fingerprint"
per utterance (mean over time), then greedy-assigns utterances to clusters
by cosine similarity. Good enough to separate clearly-different voices
(e.g. male vs female). For near-identical voices, users should rename
speakers manually via the UI.
"""
from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass, field

import numpy as np

SAMPLE_RATE = 16_000
_EMBED_DIM = 32
_SIM_THRESHOLD = 0.93  # cosine similarity; below → new cluster
_MIN_SAMPLES = SAMPLE_RATE // 4  # 250ms
_WIN = int(0.025 * SAMPLE_RATE)
_HOP = int(0.010 * SAMPLE_RATE)


def _log_mel_embedding(pcm: np.ndarray) -> np.ndarray:
    """Return a 32-dim L2-normalised log-mel fingerprint for a PCM16 chunk."""
    if pcm.size < _MIN_SAMPLES:
        return np.zeros(_EMBED_DIM, dtype=np.float32)
    f = pcm.astype(np.float32) / 32768.0
    n_frames = max(0, (f.size - _WIN) // _HOP + 1)
    if n_frames < 5:
        return np.zeros(_EMBED_DIM, dtype=np.float32)
    strides = (_HOP * f.strides[0], f.strides[0])
    frames = np.lib.stride_tricks.as_strided(
        f, shape=(n_frames, _WIN), strides=strides
    ) * np.hanning(_WIN)
    spec = np.abs(np.fft.rfft(frames, axis=1))

    nbins = _EMBED_DIM
    edges = np.logspace(np.log10(50.0), np.log10(SAMPLE_RATE / 2), nbins + 1)
    freqs = np.fft.rfftfreq(_WIN, 1.0 / SAMPLE_RATE)
    mel = np.zeros((n_frames, nbins), dtype=np.float32)
    for i in range(nbins):
        mask = (freqs >= edges[i]) & (freqs < edges[i + 1])
        if mask.any():
            mel[:, i] = spec[:, mask].mean(axis=1)
    log_mel = np.log1p(mel)
    emb = log_mel.mean(axis=0)
    n = float(np.linalg.norm(emb))
    if n > 0:
        emb = emb / n
    return emb.astype(np.float32)


@dataclass
class _ClusterState:
    centroids: list[np.ndarray] = field(default_factory=list)
    counts: list[int] = field(default_factory=list)


_sessions: dict[str, _ClusterState] = {}
_lock = threading.Lock()


def reset_session(session_id: str) -> None:
    with _lock:
        _sessions.pop(session_id, None)


def assign_speaker(session_id: str, pcm: np.ndarray) -> str:
    """Compute embedding and return SPEAKER_NN id. Creates new cluster if far."""
    emb = _log_mel_embedding(pcm)
    with _lock:
        state = _sessions.setdefault(session_id, _ClusterState())
        if np.linalg.norm(emb) < 1e-6:
            # silence / too short — fall back to whichever cluster is largest
            if state.centroids:
                idx = int(np.argmax(state.counts))
                return f"SPEAKER_{idx:02d}"
            state.centroids.append(emb)
            state.counts.append(1)
            return "SPEAKER_00"

        if state.centroids:
            sims = np.array([float(np.dot(emb, c)) for c in state.centroids])
            best = int(np.argmax(sims))
            if sims[best] >= _SIM_THRESHOLD:
                n = state.counts[best] + 1
                state.centroids[best] = (state.centroids[best] * state.counts[best] + emb) / n
                # renormalise centroid to keep cosine comparisons well-behaved
                norm = float(np.linalg.norm(state.centroids[best]))
                if norm > 0:
                    state.centroids[best] = state.centroids[best] / norm
                state.counts[best] = n
                return f"SPEAKER_{best:02d}"

        idx = len(state.centroids)
        state.centroids.append(emb)
        state.counts.append(1)
        return f"SPEAKER_{idx:02d}"


async def assign_speaker_async(session_id: str, pcm: np.ndarray) -> str:
    return await asyncio.to_thread(assign_speaker, session_id, pcm)
