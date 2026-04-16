# Architecture

## Services (docker-compose)

| Service      | Role                                                       |
|--------------|------------------------------------------------------------|
| `api`        | FastAPI HTTP + WebSocket, auth, job orchestration          |
| `asr-worker` | Celery worker: preprocessing + faster-whisper + pyannote   |
| `postgres`   | Metadata (users, jobs, sessions, transcripts, exports)     |
| `redis`      | Celery broker + WS pub/sub                                 |
| `minio`      | S3-compatible object storage (audio, exports)              |
| `flower`     | Celery task dashboard                                      |
| `frontend`   | Next.js 14 (App Router, i18n)                              |
| `nginx`      | Reverse proxy (`/api`, `/ws`, `/`)                         |

## Data flow — offline

```
client → POST /api/v1/build_protocol (multipart)
  → api: validate + store audio in MinIO + create Job(pending)
  → enqueue Celery task `process_audio(job_id)` on queue `asr`
asr-worker (stage 2 — implemented):
  1. download audio from MinIO
  2. ffmpeg → mono 16 kHz WAV with loudnorm
  3. pyannote.audio 3.1 diarization (merged adjacent turns, gap ≤ 300 ms)
  4. faster-whisper full-file transcription with VAD filter + per-language initial_prompt
     - force a language when exactly one hint given; otherwise auto-detect (handles kk↔ru code-switching)
  5. align ASR segments with diarization turns by max temporal overlap
  6. merge adjacent same-speaker-same-language segments (gap ≤ 500 ms)
  7. LLM summarization (GPT-4o, `responses.parse` → ProtocolDraft), single-pass or map-reduce
     on long transcripts; output language follows the dominant detected language (kk/ru/en)
  8. persist Speakers + TranscriptSegments + full Job.result JSON (transcript + protocol + metadata)
frontend polls /jobs/{id}
```

## Data flow — live (streaming)

```
[mic] ──PCM16 16 kHz, 200 ms chunks──▶ WS /ws/session/{id}
  → api buffers + RMS/VAD-based utterance chopping
  → on utterance end: Celery `transcribe_utterance` on queue `asr`
asr-worker:
  1. decode WAV bytes
  2. faster-whisper transcribe (forced or auto language)
  3. persist TranscriptSegment
  4. redis.publish(session:{id}, {type:"final", text, confidence, ...})
api WS fan-out → client updates live-transcript list; downloadable snapshot any time
```

Target end-to-end latency on GPU: **< 2 s** for short utterances.
