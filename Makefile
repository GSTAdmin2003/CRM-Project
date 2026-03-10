# Django CRM Project Makefile
#
# Two ports, two purposes — never mix them:
#   :8000  Django  — API + pages + built static assets   ← normal mode entry point
#   :5173  Vite    — HMR dev server ONLY                 ← make dev entry point

.PHONY: help run dev stop restart restart-be restart-fe restart-workers \
        logs logs-celery ngrok \
        db-start db-stop db-restart migrate init-db reset-db \
        fe-build fe-watch static \
        docker-build docker-down docker-up setup

# ─────────────────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "Ports"
	@echo "  :8000  Django  — API, pages, built static assets   (normal mode)"
	@echo "  :5173  Vite    — HMR dev server only               (make dev)"
	@echo ""
	@echo "App lifecycle"
	@echo "  make run              build frontend + start Docker → http://localhost:8000"
	@echo "  make dev              HMR mode: restart Django(VITE_DEV_MODE=true) + Vite → http://localhost:5173"
	@echo "  make stop             stop Docker + kill Vite + kill ngrok"
	@echo ""
	@echo "Restart  (normal mode)"
	@echo "  make restart          rebuild frontend + restart workers"
	@echo "  make restart-be       restart web + all workers  (after env/dep changes)"
	@echo "  make restart-fe       rebuild frontend  (Django auto-reloads via manifest watch)"
	@echo "  make restart-workers  restart celery + celery-beat + ari-handler"
	@echo ""
	@echo "Logs"
	@echo "  make logs             tail Django (web) logs"
	@echo "  make logs-celery      tail celery + ari-handler logs"
	@echo ""
	@echo "Database"
	@echo "  make db-start         start PostgreSQL container"
	@echo "  make db-stop          stop PostgreSQL container"
	@echo "  make db-restart       restart PostgreSQL container"
	@echo "  make migrate          makemigrations + migrate"
	@echo "  make init-db          migrate + init_settings"
	@echo "  make reset-db         wipe and recreate DB  (DESTRUCTIVE)"
	@echo ""
	@echo "Frontend"
	@echo "  make fe-build         build assets → static/dist/"
	@echo "  make fe-watch         watch + rebuild on change"
	@echo "  make static           fe-build + collectstatic  (production prep)"
	@echo ""
	@echo "Other"
	@echo "  make ngrok            expose :8000 via ngrok  (for webhooks)"
	@echo "  make docker-build     rebuild Docker images"
	@echo "  make setup            first-time: db-start + init-db + run"
	@echo ""

# ─────────────────────────────────────────────────────────────────────────────
# App lifecycle
# ─────────────────────────────────────────────────────────────────────────────

# Normal mode — :8000 is the entry point.
# Django serves the compiled manifest + built assets from static/dist/.
# Python changes auto-apply (uvicorn --reload). Re-run after Svelte changes.
run:
	@echo "Building frontend..."
	npm run build
	@echo "Starting Docker services..."
	docker compose up -d
	@echo ""
	@echo "  App  → http://localhost:8000"
	@echo "  Logs → make logs"
	@echo ""
	@echo "Webhooks: run 'make ngrok' in a separate terminal."

# HMR dev mode — :5173 is the entry point.
# Vite serves assets with hot-reload and proxies everything else to Django :8000.
# Django is reconfigured (VITE_DEV_MODE=true) to point asset URLs at Vite.
#
# After Ctrl+C: run 'make run' to return to normal mode (:8000).
dev:
	@echo "Switching to HMR mode..."
	VITE_DEV_MODE=true docker compose up -d web
	@echo ""
	@echo "  App  → http://localhost:5173  (Vite HMR — entry point)"
	@echo "  API  → http://localhost:8000  (Django — internal only)"
	@echo ""
	@echo "After Ctrl+C: run 'make run' to return to normal mode (:8000)."
	@echo ""
	VITE_DEV_MODE=true npm run dev

stop:
	@echo "Stopping Docker services..."
	docker compose stop
	@echo "Killing Vite HMR (port 5173)..."
	@kill $$(lsof -ti:5173) 2>/dev/null || true
	@echo "Killing ngrok (port 4040)..."
	@kill $$(lsof -ti:4040) 2>/dev/null || true
	@echo "Done."

# ─────────────────────────────────────────────────────────────────────────────
# Restart helpers  (normal mode — :8000)
#
# web:          uvicorn --reload-dir /app → auto-reloads on Python OR manifest changes.
# celery,       no auto-reload → must restart after task/service code changes.
# celery-beat,
# ari-handler:
# ─────────────────────────────────────────────────────────────────────────────

# Most common: rebuild frontend + restart workers after code changes.
restart: restart-workers restart-fe

# After env var or requirements changes.
restart-be:
	docker compose restart web celery celery-beat ari-handler

# After Svelte/JS changes only.
# Django auto-reloads when static/dist/.vite/manifest.json changes.
restart-fe:
	@echo "Rebuilding frontend..."
	npm run build
	@echo "Done → Django reloading from manifest change  (http://localhost:8000)"

# After Python task/service code changes only.
restart-workers:
	docker compose restart celery celery-beat ari-handler

# ─────────────────────────────────────────────────────────────────────────────
# Logs
# ─────────────────────────────────────────────────────────────────────────────

logs:
	docker compose logs -f web

logs-celery:
	docker compose logs -f celery celery-beat ari-handler

# ─────────────────────────────────────────────────────────────────────────────
# Webhooks
# ─────────────────────────────────────────────────────────────────────────────

ngrok:
	ngrok http --url=lorenzo-fatter-lovingly.ngrok-free.dev 8000

# ─────────────────────────────────────────────────────────────────────────────
# Database
# ─────────────────────────────────────────────────────────────────────────────

db-start:
	@echo "Starting PostgreSQL..."
	docker compose up -d db
	@sleep 3

db-stop:
	docker compose stop db

db-restart: db-stop
	@sleep 2
	$(MAKE) db-start

migrate:
	docker compose run --rm web python manage.py makemigrations
	docker compose run --rm web python manage.py migrate

init-db: migrate
	docker compose run --rm web python manage.py init_settings

reset-db:
	@echo "WARNING: This will destroy all database data!"
	@echo "Press Ctrl+C to cancel, or Enter to continue..."
	@read dummy
	docker compose down db
	docker compose rm -f db
	$(MAKE) db-start
	@sleep 5
	find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
	find . -path "*/migrations/*.pyc" -delete
	docker compose run --rm web python manage.py makemigrations
	docker compose run --rm web python manage.py migrate
	docker compose run --rm web python manage.py createsuperuser \
		--noinput --username admin --email admin@example.com \
		|| echo "Superuser already exists"
	docker compose run --rm web python manage.py init_settings
	@echo "Database reset complete."

# ─────────────────────────────────────────────────────────────────────────────
# Frontend  (Vite build — feeds normal mode at :8000)
# ─────────────────────────────────────────────────────────────────────────────

fe-build:
	npm run build

fe-watch:
	npm run build -- --watch

# Build + collect for production deployment.
static: fe-build
	docker compose run --rm web python manage.py collectstatic --no-input

# ─────────────────────────────────────────────────────────────────────────────
# Docker helpers
# ─────────────────────────────────────────────────────────────────────────────

docker-build:
	docker compose build

docker-down:
	docker compose down

docker-up:
	docker compose up -d

# ─────────────────────────────────────────────────────────────────────────────
# First-time setup
# ─────────────────────────────────────────────────────────────────────────────

setup:
	$(MAKE) db-start
	$(MAKE) init-db
	$(MAKE) run
