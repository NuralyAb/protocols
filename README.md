# Protocol AI — AI-Протоколист заседаний

Meeting protocol system with speech recognition, speaker diarization and LLM-based
summarization.

Supported languages: **Kazakh (kk), Russian (ru), English (en)** — including
code-switching (KK↔RU in a single recording).

## Stack

- **Backend:** Python 3.11, FastAPI, Celery, PostgreSQL, Redis, MinIO
- **ML:** faster-whisper, pyannote.audio, GPT-4o (structured output)
- **Frontend:** Next.js 14 (App Router), TypeScript, TailwindCSS
- **Infra:** Docker Compose, Nginx, GPU via nvidia-container-toolkit

## Quickstart

```bash
cp .env.example .env
# edit secrets (OPENAI_API_KEY, HUGGINGFACE_TOKEN, POSTGRES_PASSWORD, etc.)

make dev          # up all services
make migrate      # apply Alembic migrations
make seed         # optional: seed demo user
make logs         # tail logs
make down         # stop
```

Services after `make dev`:

| Service   | URL                        |
|-----------|----------------------------|
| Frontend  | http://localhost:3000      |
| API       | http://localhost:8000      |
| Swagger   | http://localhost:8000/docs |
| MinIO     | http://localhost:9001      |
| Flower    | http://localhost:5555      |

## Roadmap

1. ✅ Scaffold — docker-compose, skeletons, DB, auth
2. ✅ Offline ASR pipeline (Whisper + pyannote, kk/ru/en)
3. ✅ LLM summarization (agenda, decisions, action items)
4. ✅ Export PDF/DOCX/JSON/TXT/SRT/VTT
5. ✅ Frontend MVP
6. ✅ Real-time audio (WebSocket + streaming Whisper)
7. ⏳ Polish, accessibility audit, production deploy

## Docs

- [`docs/architecture.md`](docs/architecture.md)
- [`docs/api.md`](docs/api.md)
- [`docs/deployment.md`](docs/deployment.md)
