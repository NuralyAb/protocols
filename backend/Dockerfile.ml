# GPU-enabled image for Celery ASR / sign workers.
# Falls back to CPU if no GPU is available; set ASR_DEVICE=cpu in .env.
FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04 AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=UTC \
    HF_HOME=/ml-models/hf-cache \
    TRANSFORMERS_CACHE=/ml-models/hf-cache

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.11 python3.11-venv python3-pip \
        ffmpeg libsndfile1 libmagic1 libpq-dev \
        build-essential git curl ca-certificates \
    && ln -sf /usr/bin/python3.11 /usr/bin/python \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Web + infra deps
RUN pip install --upgrade pip && pip install \
    "fastapi>=0.115" "uvicorn[standard]>=0.32" \
    "pydantic>=2.9" "pydantic-settings>=2.6" \
    "sqlalchemy[asyncio]>=2.0" "asyncpg>=0.30" "psycopg[binary]>=3.2" "alembic>=1.14" \
    "redis>=5.2" "celery[redis]>=5.4" "flower>=2.0" \
    "boto3==1.35.36" "aioboto3==13.2.0" "httpx>=0.27" "structlog>=24.4" \
    "python-jose[cryptography]>=3.3" "passlib>=1.7" "bcrypt==4.0.1" "email-validator>=2.2" \
    "orjson>=3.10" "tenacity>=9.0" "python-multipart>=0.0.17" \
    "jinja2>=3.1" "python-docx>=1.1"

# ML deps (torch CUDA 12.1 wheels are ABI-compatible with CUDA 12.x runtime)
RUN pip install --index-url https://download.pytorch.org/whl/cu121 \
    "torch==2.4.1" "torchaudio==2.4.1"

RUN pip install \
    "faster-whisper>=1.0.3" \
    "pyannote.audio>=3.3.0" \
    "numpy>=1.26" "scipy>=1.13" \
    "soundfile>=0.12" "librosa>=0.10" \
    "ffmpeg-python>=0.2" \
    "silero-vad>=5.1" \
    "openai>=1.54" \
    "websockets>=13" \
    "transformers>=4.45" \
    "huggingface_hub>=0.25"

COPY . .

CMD ["celery", "-A", "app.workers.celery_app", "worker", "-l", "info", "-c", "1"]
