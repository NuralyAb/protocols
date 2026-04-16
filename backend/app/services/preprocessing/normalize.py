"""Decode any supported audio/video container → mono 16 kHz WAV via ffmpeg."""
from __future__ import annotations

import subprocess
from pathlib import Path


def to_wav_16k_mono(src: str | Path, dst: str | Path, loudnorm: bool = True) -> Path:
    src = str(src)
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)

    af = "loudnorm=I=-23:TP=-1.5:LRA=11" if loudnorm else "anull"
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", src,
        "-ac", "1", "-ar", "16000",
        "-af", af,
        "-f", "wav",
        str(dst),
    ]
    subprocess.run(cmd, check=True)
    return dst


def probe_duration_ms(path: str | Path) -> int:
    out = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    try:
        return int(float(out) * 1000)
    except ValueError:
        return 0
