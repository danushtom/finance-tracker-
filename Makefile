SHELL := cmd.exe
.SHELLFLAGS := /c

# ── Config ────────────────────────────────────────────────────────────────────
API_PORT  := 8000
WEB_PORT  := 3000

# Override the Docker-targeted MONGODB_URI from .env with the local one.
# All other vars (JWT_SECRET, etc.) are read from .env by pydantic-settings
# automatically because we run commands from the repo root where .env lives.
export MONGODB_URI             := mongodb://localhost:27017/?replicaSet=rs0
export NEXT_PUBLIC_API_BASE_URL := http://localhost:$(API_PORT)/api/v1

.PHONY: install api worker web seed seed-user \
        test test-backend test-frontend \
        lint fmt backup restore

# ── Setup ─────────────────────────────────────────────────────────────────────

## Install all backend + frontend dependencies
install:
	cd backend && python -m venv .venv && .venv\Scripts\python -m pip install -e ".[dev]"
	cd frontend && npm install

# ── Run (local dev) ───────────────────────────────────────────────────────────
# Commands run from the repo root so pydantic-settings finds .env at ./
# PYTHONPATH=backend lets Python import the `app` package.

## Start the FastAPI backend with hot-reload
api:
	set PYTHONPATH=backend&& backend\.venv\Scripts\uvicorn app.main:app --reload --host 0.0.0.0 --port $(API_PORT)

## Start the background worker
worker:
	set PYTHONPATH=backend&& backend\.venv\Scripts\python -m app.worker.runner

## Start the Next.js frontend dev server
web:
	cd frontend && npm run dev

## Create the default demo user (demo@example.com / demo1234)
seed:
	set PYTHONPATH=backend&& backend\.venv\Scripts\python backend\scripts\create_demo_user.py

## Create a user with custom creds: make seed-user EMAIL=you@example.com PASSWORD=secret NAME="Your Name"
seed-user:
	set PYTHONPATH=backend&& backend\.venv\Scripts\python backend\scripts\create_demo_user.py --email "$(EMAIL)" --password "$(PASSWORD)" --name "$(NAME)"

# ── Tests ─────────────────────────────────────────────────────────────────────

test-backend:
	set PYTHONPATH=backend&& backend\.venv\Scripts\pytest backend\tests

test-frontend:
	cd frontend && npm run test

test: test-backend test-frontend

# ── Code quality ──────────────────────────────────────────────────────────────

lint:
	backend\.venv\Scripts\ruff check backend\app
	cd frontend && npm run lint

fmt:
	backend\.venv\Scripts\ruff format backend\app
	cd frontend && npm run format

# ── Backup / restore ──────────────────────────────────────────────────────────

backup:
	mongodump --uri="$(MONGODB_URI)" --db=finance_tracker --archive=backups\backup.archive

restore:
	mongorestore --uri="$(MONGODB_URI)" --archive=$(FILE) --nsInclude="finance_tracker.*" --drop
