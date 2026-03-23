# CRM System

A full-featured sales CRM built on Django + Svelte, with VoIP (Asterisk), async task processing (Celery), and AI-assisted call analysis.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5.1.4, Python 3.12, Django REST Framework 3.15 |
| Database | PostgreSQL 15 |
| Cache / Broker | Redis 7 |
| Async Tasks | Celery 5.3 (worker + beat) |
| VoIP | Asterisk 20 (ARI WebSocket) |
| Frontend | Svelte 4 + Vite, Tailwind CSS, Alpine.js, HTMX |
| AI | Claude (call analysis), ElevenLabs Scribe (transcription) |
| Containers | Docker Compose |

---

## Architecture

### App Layout

```
CRM Project/
├── core/                        # Shared foundation
│   ├── models.py                # User, Role, UserRole
│   ├── permissions.py           # Role-based permission classes
│   ├── middleware.py            # RoleBasedAccessMiddleware
│   ├── exceptions.py            # ServiceError hierarchy
│   └── migrations/
│
├── apps/
│   ├── crm/                     # Leads, opportunities, pipeline (Kanban)
│   ├── contacts/                # Companies and contacts
│   ├── activities/              # Tasks, calls, meetings linked to leads
│   ├── calls/                   # Asterisk call records, recordings, transcription
│   ├── messaging/               # WhatsApp conversations
│   └── user_settings/           # Settings UI + user/role management
│
├── frontend/
│   ├── src/
│   │   ├── components/          # Svelte components (one folder per page/feature)
│   │   ├── entries/             # Vite entry points (one per page)
│   │   └── stores/              # Svelte stores (leadStore, uiStore)
│   └── vite.config.js
│
├── templates/                   # Django base templates (Svelte island shells)
├── static/dist/                 # Compiled Svelte assets (git-ignored, built by Vite)
├── docker-compose.yml
├── Makefile                     # All dev commands — see below
└── requirements.txt
```

### Standard App Structure

Every app under `apps/` follows this layout:

```
apps/<app>/
  models/          # One file per model group; __init__.py re-exports all
  services/        # Business logic — stateless, no HTTP objects
  serializers/     # DRF serializers
  views/
    <entity>_views.py    # DRF ViewSets / APIViews
    template_views.py    # Django template views (Svelte island shells)
  tests/
    conftest.py          # factory_boy factories
    test_models.py
    test_services.py
    test_api.py
  migrations/
```

### Frontend Pattern — Svelte Islands

Each page is a minimal Django template containing:
1. A `<script type="application/json">` tag with serialized init data
2. A `<div id="svelte-*-root">` mount target
3. A corresponding Vite entry (`frontend/src/entries/*.js`) that mounts the Svelte component

Django serves pre-built assets at `:8000`. Vite HMR at `:5173` proxies everything else to Django.

### Docker Services

| Service | Description |
|---|---|
| `web` | Django (uvicorn, `--reload`) — `:8000` |
| `db` | PostgreSQL 15 — `:5433` (host) / `:5432` (container) |
| `redis` | Redis 7 — `:6379` |
| `asterisk` | Asterisk 20 — SIP `:5060/udp`, ARI `:8088`, RTP `:10000-10100/udp` |
| `celery` | Celery worker |
| `celery-beat` | Celery periodic task scheduler |
| `ari-handler` | Long-running ARI WebSocket event handler (`run_ari_handler`) |
| `autoheal` | Auto-restarts unhealthy containers |

### Role Hierarchy

Roles are hierarchical — each level includes all levels above it:

```
Owner
└── Sales Director   is_sales_director()  — sees and manages everything
    └── Sales Manager   is_sales_manager()  — manages team(s) and agents
        └── Sales Agent   is_sales_agent()   — manages own leads
IT Admin             — access to SIP/VoIP settings
```

### Lead / Opportunity Model

A single `Lead` model uses `status` as the sole discriminator:

| Status | Shown in |
|---|---|
| `new` | Lead list (`/crm/leads/`) |
| `converted` | Kanban board (pipeline opportunities) |
| `won` | Won deals |
| `lost` | Lost deals |

---

## Prerequisites

- Docker + Docker Compose
- Node.js 18+ and npm

---

## First-Time Setup

```bash
# 1. Copy and fill in environment variables
cp .env.example .env

# 2. One-command setup: starts DB, runs migrations, builds frontend, starts all services
make setup
```

The app will be available at **http://localhost:8000**.

---

## Daily Development

### Normal mode (`:8000`)

Django serves pre-compiled Svelte assets. Python changes hot-reload automatically.

```bash
make run          # build frontend + start all Docker services
make stop         # stop everything
```

After editing Python code — no action needed (uvicorn `--reload` picks it up).

After editing Svelte/JS:

```bash
make restart-fe   # rebuild frontend + restart web
```

After editing Celery tasks or services:

```bash
make restart-workers   # restart celery + celery-beat + ari-handler
```

### HMR dev mode (`:5173`)

Vite serves assets with hot-reload and proxies everything else to Django.

```bash
make dev          # switches Django to VITE_DEV_MODE=true + starts Vite HMR
# → open http://localhost:5173
# Ctrl+C to stop Vite, then:
make run          # return to normal mode
```

---

## All Make Commands

```bash
make help         # print this list with descriptions
```

| Command | Description |
|---|---|
| `make run` | Build frontend + start all services → `:8000` |
| `make dev` | HMR mode: Django + Vite → `:5173` |
| `make stop` | Stop Docker + kill Vite + kill ngrok |
| `make restart` | Rebuild frontend + restart web + restart workers |
| `make restart-be` | Restart web + all workers (after env/dep changes) |
| `make restart-fe` | Rebuild frontend + restart web only |
| `make restart-workers` | Restart celery + celery-beat + ari-handler |
| `make logs` | Tail Django (web) logs |
| `make logs-celery` | Tail celery + ari-handler logs |
| `make migrate` | `makemigrations` + `migrate` |
| `make init-db` | `migrate` + `init_settings` |
| `make reset-db` | **Destructive** — wipe DB, delete migrations, start fresh |
| `make fe-build` | Build Svelte assets → `static/dist/` |
| `make fe-watch` | Watch + rebuild on change |
| `make static` | `fe-build` + `collectstatic` (production prep) |
| `make docker-build` | Rebuild Docker images |
| `make ngrok` | Expose `:8000` via ngrok (for webhooks) |
| `make setup` | First-time: `db-start` + `init-db` + `run` |

---

## Environment Variables

Copy `.env.example` to `.env` and fill in:

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `1` for development, `0` for production |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | Database credentials |
| `ARI_USER` / `ARI_PASSWORD` | Asterisk ARI credentials |
| `EXTERNAL_IP` | Server's public IP (for Asterisk NAT) |
| `TZ` | Timezone (e.g. `Asia/Tbilisi`) |

AI / integration keys are stored in the database via **Settings → Transcription** (ElevenLabs, Anthropic).

---

## Running Tests

Tests run inside Docker against the real database:

```bash
docker compose run --rm web python -m pytest apps/<app>/tests/ -v
```

Run all tests:

```bash
docker compose run --rm web python -m pytest -v
```

**Note**: Use `api_client.force_login(user)` in API tests — not `force_authenticate` — because `RoleBasedAccessMiddleware` checks `request.user.is_authenticated` at the Django layer before DRF runs.

---

## Useful URLs

| URL | Description |
|---|---|
| `http://localhost:8000` | Application |
| `http://localhost:8000/admin` | Django admin |
| `http://localhost:8000/settings` | Settings (roles, users, VoIP, AI) |
| `http://localhost:8000/crm/leads` | Lead list |
| `http://localhost:8000/crm/kanban` | Opportunity pipeline (Kanban) |
