"""Lightweight denoise via ffmpeg afftdn. Optional — off by default."""
from __future__ import annotations

import subprocess
from pathlib import Path


def denoise(src: str | Path, dst: str | Path, strength: float = 12.0) -> Path:
    src = str(src)
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", src,
        "-af", f"afftdn=nr={strength}",
        "-ac", "1", "-ar", "16000",
        "-f", "wav",
        str(dst),
    ]
    subprocess.run(cmd, check=True)
    return dst
