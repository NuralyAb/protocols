# HTTP API

Base: `http://localhost:8000/api/v1`. OpenAPI live at `/docs`.

## Auth
- `POST /auth/register` — `{email, password, full_name?}` → `UserOut`
- `POST /auth/login` — `{email, password}` → `{access_token, refresh_token}`
- `GET  /auth/me` — `Authorization: Bearer …` → `UserOut`

## Jobs (offline)
- `POST   /build_protocol` — multipart `file=audio` → `{job_id, status}` (202)
- `GET    /jobs` — list owned jobs
- `GET    /jobs/{id}` → status + progress
- `GET    /jobs/{id}/result` → full protocol snapshot
- `PATCH  /jobs/{id}/speakers` — `[{diarization_id, label?, role?}]`
- `GET    /jobs/{id}/export?format=pdf|docx|json|srt|vtt|txt`

## Live sessions
- `POST /sessions` — `{title?, languages[]}`
- `GET  /sessions/{id}`
- `GET  /sessions/{id}/snapshot` — downloadable protocol snapshot at any moment
- `GET  /sessions/{id}/export?format=pdf|docx|json|srt|vtt|txt`
- `PATCH /sessions/{id}/speakers` — rename speakers / assign roles
- `WS   /ws/session/{id}?token=...` — PCM16 chunks in, transcript events out:
  - `{type:"ready", language}`
  - `{type:"utterance_queued", start_ms, end_ms}`
  - `{type:"final", speaker, language, start_ms, end_ms, text, confidence}`
  - `{type:"error", message}`
  - control IN: `{type:"end"}`

## Response shape (protocol)
See `backend/app/api/v1/schemas/jobs.py` and canonical JSON in the project README.
