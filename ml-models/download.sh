#!/usr/bin/env bash
# Download ASR + sign-language weights into ./ml-models. Stages 2 & 8 wire them in.
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$DIR/asr" "$DIR/sign"

: "${HUGGINGFACE_TOKEN:=}"

# faster-whisper (CTranslate2) large-v3
python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download(repo_id="Systran/faster-whisper-large-v3", local_dir="ml-models/asr/faster-whisper-large-v3")
PY

# Kazakh fine-tune (optional — requires HF token)
if [[ -n "$HUGGINGFACE_TOKEN" ]]; then
python - <<'PY'
import os
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id=os.environ.get("ASR_KAZAKH_MODEL", "issai/whisper-large-v3-kazakh"),
    local_dir="ml-models/asr/kazakh",
    token=os.environ["HUGGINGFACE_TOKEN"],
)
PY
fi

echo "done."
