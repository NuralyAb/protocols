COMPOSE := docker compose -f infra/docker-compose.yml --env-file .env

.PHONY: help dev up down logs build rebuild migrate revision seed shell-api shell-db test lint fmt clean

help:
	@echo "dev       - build & up all services"
	@echo "up        - start services"
	@echo "down      - stop services"
	@echo "logs      - tail logs"
	@echo "build     - build images"
	@echo "rebuild   - build --no-cache"
	@echo "migrate   - alembic upgrade head"
	@echo "revision  - alembic autogenerate revision (m=...)"
	@echo "seed      - seed demo data"
	@echo "shell-api - bash in api container"
	@echo "shell-db  - psql into postgres"
	@echo "test      - run backend+frontend tests"
	@echo "lint      - ruff + eslint"
	@echo "fmt       - ruff format + prettier"

dev: build up migrate
up:
	$(COMPOSE) up -d
down:
	$(COMPOSE) down
logs:
	$(COMPOSE) logs -f --tail=200
build:
	$(COMPOSE) build
rebuild:
	$(COMPOSE) build --no-cache

migrate:
	$(COMPOSE) exec api alembic upgrade head

revision:
	$(COMPOSE) exec api alembic revision --autogenerate -m "$(m)"

seed:
	$(COMPOSE) exec api python -m app.db.seed

shell-api:
	$(COMPOSE) exec api bash

shell-db:
	$(COMPOSE) exec postgres psql -U $$POSTGRES_USER -d $$POSTGRES_DB

test:
	$(COMPOSE) exec api pytest -q
	$(COMPOSE) exec frontend npm test --silent || true

lint:
	$(COMPOSE) exec api ruff check app
	$(COMPOSE) exec frontend npm run lint

fmt:
	$(COMPOSE) exec api ruff format app
	$(COMPOSE) exec frontend npm run format

clean:
	$(COMPOSE) down -v
	rm -rf infra/volumes
