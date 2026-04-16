# Deployment

## Local development (Docker Desktop)

```bash
cp .env.example .env
# fill HUGGINGFACE_TOKEN, OPENAI_API_KEY, POSTGRES_PASSWORD, APP_SECRET_KEY
make dev
make migrate
make seed
```

Open:
- Frontend — http://localhost:3000
- API docs — http://localhost:8000/docs
- MinIO console — http://localhost:9001 (creds from `.env`)
- Flower — http://localhost:5555

## Production (single GPU VPS, Ubuntu 24.04)

### 1. Prepare host

```bash
# Docker + compose plugin
sudo apt update && sudo apt install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER && newgrp docker

# NVIDIA driver + container toolkit (GPU transcription)
sudo apt install -y nvidia-driver-550   # or latest; reboot after
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt update && sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Sanity check
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

### 2. TLS via Let's Encrypt

```bash
sudo apt install -y certbot
# Initial certificate (domain must already point to the host)
sudo certbot certonly --standalone -d YOUR_DOMAIN
# Renewal is automatic via /etc/cron.d/certbot

# Edit infra/nginx/nginx.prod.conf — replace YOUR_DOMAIN with the real name.
```

### 3. Clone + configure

```bash
git clone <your-fork> /opt/protocol-ai
cd /opt/protocol-ai

cp .env.prod.example .env.prod
# fill real secrets. Generate APP_SECRET_KEY:
python3 -c "import secrets; print(secrets.token_urlsafe(48))"

sudo mkdir -p /var/lib/protocol-ai/{pgdata,minio,ml-models}
```

### 4. Bring it up

```bash
docker compose -f infra/docker-compose.prod.yml --env-file .env.prod build
docker compose -f infra/docker-compose.prod.yml --env-file .env.prod up -d

# Apply migrations and seed the first user
docker compose -f infra/docker-compose.prod.yml --env-file .env.prod exec api alembic upgrade head
docker compose -f infra/docker-compose.prod.yml --env-file .env.prod exec api python -m app.db.seed
```

### 5. Verify

- `curl https://YOUR_DOMAIN/api/v1/auth/me` → 401 (auth required, TLS works).
- `curl -k https://YOUR_DOMAIN/openapi.json | jq '.info.title'` → `"Protocol AI"`.
- Open `https://YOUR_DOMAIN` in a browser — login with seeded demo user (change the password after first login).

### 6. Updates

```bash
cd /opt/protocol-ai && git pull
docker compose -f infra/docker-compose.prod.yml --env-file .env.prod build api frontend asr-worker
docker compose -f infra/docker-compose.prod.yml --env-file .env.prod up -d
docker compose -f infra/docker-compose.prod.yml --env-file .env.prod exec api alembic upgrade head
```

## Monitoring

- **Logs:** `docker compose -f infra/docker-compose.prod.yml logs -f api asr-worker`
  — requests are tagged with `X-Trace-Id`, search by `trace_id=<id>`.
- **Celery queue:** proxy Flower only on admin endpoint if exposed; otherwise `docker exec api celery -A app.workers.celery_app inspect active`.
- **GPU:** `watch -n5 nvidia-smi` on the host.

## Scaling

- For more concurrent live sessions: horizontal-scale `asr-worker` (`--scale asr-worker=3`). Redis pub/sub fans out transcripts to all API replicas.
- For more HTTP throughput: set `-w` on gunicorn higher or scale `api`; Nginx round-robins.
- Storage: point `S3_ENDPOINT` at managed S3 (AWS, Yandex Object Storage) — MinIO is only for self-hosted PoC.

## Backup

- Postgres: nightly `pg_dump` to off-site storage.
- MinIO: `mc mirror` the `protocol-media` and `protocol-exports` buckets.
- DB migrations are idempotent — no data loss on upgrade. Always snapshot before Alembic version jumps.
