from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = True
    app_secret_key: str = "change-me"

    # JWT
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_min: int = 60
    jwt_refresh_ttl_days: int = 14

    # CORS
    api_cors_origins: str = "http://localhost:3000"

    # DB
    database_url: str
    alembic_database_url: str

    # Redis / Celery
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # S3
    s3_endpoint: str = "http://minio:9000"
    s3_public_endpoint: str = "http://localhost:9000"
    s3_region: str = "us-east-1"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_media: str = "protocol-media"
    s3_bucket_exports: str = "protocol-exports"

    # ML
    huggingface_token: str = ""
    openai_api_key: str = ""
    llm_provider: Literal["openai", "local"] = "openai"
    llm_model: str = "gpt-4o"

    asr_provider: Literal["openai", "local"] = "local"
    openai_asr_model: str = "gpt-4o-transcribe"
    openai_asr_fallback: str = "whisper-1"
    openai_realtime_model: str = "gpt-4o-realtime-preview-2024-12-17"

    asr_model: str = "large-v3"
    asr_device: Literal["cuda", "cpu"] = "cuda"
    asr_compute_type: str = "float16"
    asr_kazakh_model: str = "issai/whisper-large-v3-kazakh"
    diarization_model: str = "pyannote/speaker-diarization-3.1"

    # Protocol templates (directory with manifest.json + <id>.md files)
    templates_dir: str = ""  # empty → resolve to repo-root "образцы/" at runtime

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
