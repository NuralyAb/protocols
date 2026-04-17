FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        ffmpeg \
        libsndfile1 \
        libmagic1 \
        libpq-dev \
        curl \
        git \
        # WeasyPrint runtime + Kazakh/Cyrillic/Latin Unicode fonts
        libpango-1.0-0 libpangoft2-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 \
        libharfbuzz0b libffi-dev shared-mime-info \
        fonts-noto fonts-noto-core fonts-noto-cjk fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
# Install minimal deps first (fast iteration). Heavy ML stack is installed by workers at runtime / Dockerfile.ml.
RUN pip install --upgrade pip && pip install \
    "fastapi>=0.115" "uvicorn[standard]>=0.32" "gunicorn>=23.0" \
    "pydantic>=2.9" "pydantic-settings>=2.6" "python-multipart>=0.0.17" \
    "python-jose[cryptography]>=3.3" "passlib>=1.7" "bcrypt==4.0.1" "email-validator>=2.2" \
    "sqlalchemy[asyncio]>=2.0" "asyncpg>=0.30" "psycopg[binary]>=3.2" "alembic>=1.14" \
    "redis>=5.2" "celery[redis]>=5.4" "flower>=2.0" \
    "boto3==1.35.36" "aioboto3==13.2.0" "httpx>=0.27" "structlog>=24.4" \
    "slowapi>=0.1.9" "tenacity>=9.0" "orjson>=3.10" \
    "jinja2>=3.1" "python-docx>=1.1" "weasyprint>=63.0" \
    "numpy>=1.26" "websockets>=13" "openai>=1.54" \
    "python-telegram-bot>=21" \
    "gradio-client>=1.0"

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
