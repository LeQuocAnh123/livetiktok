.PHONY: install install-fe setup dev-backend dev-frontend test lint db-migrate db-reset up down logs build

# === SETUP ===
install:
	pip install -e .
	pip install -e "backend/[dev]"

install-fe:
	cd frontend && npm install

setup: install
	@cp -n backend/.env.example backend/.env 2>/dev/null || true
	@echo "✅ Setup done. Edit backend/.env with your SECRET_KEY and API keys before running."

# === DEVELOPMENT ===
dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

# === DATABASE ===
db-migrate:
	cd backend && alembic upgrade head

db-reset:
	cd backend && alembic downgrade base && alembic upgrade head

# === TESTING ===
test:
	cd backend && python -m pytest tests/ -v --cov=app --cov-report=term-missing

lint:
	cd backend && ruff check app/ tests/

# === PRODUCTION (Docker) ===
up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

build:
	docker compose build
