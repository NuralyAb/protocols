"""Sync SQLAlchemy session for Celery workers (Celery tasks are sync by default)."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_settings = get_settings()

# alembic_database_url uses psycopg (sync) — reuse it for workers.
sync_engine = create_engine(_settings.alembic_database_url, pool_pre_ping=True)
SyncSessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False, class_=Session)
