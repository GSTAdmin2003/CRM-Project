# Django CRM Project Makefile
# Commands for running, restarting, and managing the application

.PHONY: help run restart stop start dev logs db-start db-stop db-restart setup migrate init-db reset-db ngrok \
        fe-dev fe-build fe-watch static

# Default target
help:
	@echo "Available commands:"
	@echo ""
	@echo "🚀 Application Commands:"
	@echo "  make run        - Start Django + Vite + ngrok (full dev environment)"
	@echo "  make restart    - Stop and restart the Django server"
	@echo "  make stop       - Stop all services"
	@echo "  make logs       - Show Django server logs"
	@echo ""
	@echo "🗄️  Database Commands:"
	@echo "  make db-start   - Start PostgreSQL database (docker)"
	@echo "  make db-stop    - Stop PostgreSQL database (docker)"
	@echo "  make db-restart - Restart PostgreSQL database (docker)"
	@echo "  make migrate    - Run Django migrations"
	@echo "  make init-db    - Initialize database with migrations and settings"
	@echo "  make reset-db   - Reset database (WARNING: destroys all data)"
	@echo ""
	@echo "🎨 Frontend Commands:"
	@echo "  make fe-dev     - Start Vite dev server (HMR on port 5173)"
	@echo "  make fe-build   - Build Svelte/Tailwind assets to static/dist/"
	@echo "  make fe-watch   - Build in watch mode (no HMR, useful with runserver)"
	@echo "  make static     - fe-build + collectstatic (production prep)"
	@echo ""
	@echo "⚡ Quick Setup:"
	@echo "  make setup      - Full setup: start db, migrate, init settings, run server"

# Start full dev environment: Django + Vite HMR + ngrok
run:
	@echo "Starting Django + Vite + ngrok..."
	@docker compose up -d web
	@npm run dev > /dev/null 2>&1 &
	@ngrok http --url=lorenzo-fatter-lovingly.ngrok-free.dev 8000 > /dev/null 2>&1 &
	@echo "✅ All services started. App → http://localhost:8000"

# Stop all dev services
stop:
	@echo "Stopping all services..."
	@docker compose stop
	@kill $$(lsof -ti:5173) 2>/dev/null || true
	@kill $$(lsof -ti:4040) 2>/dev/null || true

# Restart Django server
restart:
	@echo "Restarting Docker services..."
	docker compose restart web

# Show logs
logs:
	@echo "Showing Docker logs..."
	docker compose logs -f web

# Database Commands
db-start:
	@echo "Starting PostgreSQL database..."
	docker compose up -d db
	@echo "Waiting for database to be ready..."
	@sleep 3

db-stop:
	@echo "Stopping PostgreSQL database..."
	docker compose stop db

db-restart: db-stop
	@sleep 2
	@make db-start

# Django database operations
migrate:
	@echo "Running Django migrations..."
	docker compose run --rm web python manage.py makemigrations
	docker compose run --rm web python manage.py migrate

init-db: migrate
	@echo "Initializing database with default data..."
	docker compose run --rm web python manage.py init_settings
	@echo "Database initialization complete!"

reset-db:
	@echo "⚠️  WARNING: This will destroy all database data!"
	@echo "Press Ctrl+C to cancel, or press Enter to continue..."
	@read dummy
	@echo "Stopping and removing database container..."
	docker compose down db
	docker compose rm -f db
	@echo "Starting fresh database..."
	@make db-start
	@sleep 5
	@echo "Resetting Django database..."
	find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
	find . -path "*/migrations/*.pyc" -delete
	docker compose run --rm web python manage.py makemigrations
	docker compose run --rm web python manage.py migrate
	@echo "Creating superuser..."
	docker compose run --rm web python manage.py createsuperuser --noinput --username admin --email admin@example.com || echo "Superuser already exists"
	docker compose run --rm web python manage.py init_settings
	@echo "Database reset complete!"

# Full setup command
setup:
	@echo "🚀 Starting full application setup..."
	@make db-start
	@sleep 3
	@make init-db
	@echo "✅ Setup complete! Starting server..."
	@make run

# Frontend Commands
fe-dev:
	@echo "Starting Vite dev server on port 5173 (HMR enabled)..."
	npm run dev

fe-build:
	@echo "Building frontend assets to static/dist/..."
	npm run build

fe-watch:
	@echo "Building frontend in watch mode..."
	npm run build -- --watch

static: fe-build
	@echo "Collecting static files..."
	docker compose run --rm web python manage.py collectstatic --no-input

# Additional Docker commands
docker-build:
	@echo "Building Docker images..."
	docker compose build

docker-down:
	@echo "Stopping and removing all containers..."
	docker compose down

docker-up:
	@echo "Starting all services..."
	docker compose up -d