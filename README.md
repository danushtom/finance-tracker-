# Finance Tracker

A personal finance tracker that turns bank statements into a single, explainable
**Safe-to-Spend** number, separates baseline income from unreliable project income,
and tracks a wishlist/goals plan against real cash flow. See
[`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) and
[`docs/TECHNICAL_DESIGN.md`](docs/TECHNICAL_DESIGN.md) for the full spec this was
built from.

## Stack

- **Backend**: FastAPI + Motor (async MongoDB) + a Mongo-backed job queue/worker
- **Frontend**: Next.js 16 (App Router, Turbopack) + TypeScript strict + TanStack Query
- **Database**: MongoDB 7, single-node replica set (required for multi-document
  transactions — see `docs/TECHNICAL_DESIGN.md` ADR-7)
- **LLM categorisation fallback**: pluggable — **Gemini or Claude, chosen per user**
  (see [Configuring the LLM provider](#configuring-the-llm-provider) below). The app
  is fully usable with the LLM turned off entirely (rules-only categorisation).

---

## Quick start (Docker — recommended)

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

- `JWT_SECRET` — required, no default. Generate one with:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(48))"
  ```
- Optionally `GEMINI_API_KEY` and/or `ANTHROPIC_API_KEY` if you want the LLM
  categorisation fallback available system-wide by default (users can also set
  their own key from the Settings screen — see below).

Start all services:

```bash
docker compose up -d --build
```

This starts four services: `mongo` (with a one-shot `mongo-init` container that
runs `rs.initiate()`), `api`, `worker`, and `web`.

- **Web app**: http://localhost:3000
- **API docs**: http://localhost:8000/docs

### Creating your first account

**Option A — Register via the web UI** (simplest):

Open http://localhost:3000 and click **"Register"**. Fill in any email and
password — the seed service automatically creates default categories and
categorisation rules for you.

**Option B — Seed a demo account via CLI** (useful for demos / CI):

```bash
# Creates demo@example.com / demo1234
docker compose exec api python scripts/create_demo_user.py

# Or with custom credentials
docker compose exec api python scripts/create_demo_user.py \
  --email me@example.com \
  --password mysecret \
  --name "William"
```

> **Note:** `REGISTRATION_INVITE_CODE` in `.env` is empty by default (open
> registration). If you set it, pass `--invite` to the script or use the invite
> field on the registration form.

---

## Running locally in dev mode (without Docker)

Use this when you want fast hot-reload for both frontend and backend without
rebuilding Docker images.

### Prerequisites

- Python 3.11+
- Node 20+
- A running MongoDB 7 instance as a **replica set** (required for multi-document
  transactions). The easiest way is to keep only the `mongo` service running in
  Docker while running everything else locally:

  ```bash
  docker compose up -d mongo mongo-init
  ```

  This starts MongoDB on `localhost:27017` and initialises the `rs0` replica set.

---

### Backend (FastAPI)

```bash
cd backend

# Create and activate the virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# Install all dependencies (including dev)
pip install -e ".[dev]"

# Set environment variables for local dev
# The .env file at the repo root works — just point MONGODB_URI at localhost
export MONGODB_URI="mongodb://localhost:27017/?replicaSet=rs0"
# (PowerShell: $env:MONGODB_URI = "mongodb://localhost:27017/?replicaSet=rs0")

# Start the API with hot-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API is now available at http://localhost:8000 (interactive docs at
http://localhost:8000/docs).

**Seed a demo user locally:**

```bash
# With the venv active and MONGODB_URI set:
python scripts/create_demo_user.py
# → Creates demo@finance.local / demo1234
```

**Start the background worker** (needed for CSV/statement import processing):

```bash
# In a separate terminal, with the same venv and env vars:
python -m app.worker.runner
```

---

### Frontend (Next.js)

```bash
cd frontend

# Install dependencies
npm install

# Point the app at your locally running API
# Create a .env.local file (git-ignored by default):
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1" > .env.local

# Start the Next.js dev server with hot-reload
npm run dev
```

The web app is now available at http://localhost:3000.

---

## Configuring the LLM provider

Categorisation of unknown merchants (FR-4) can fall back to an LLM once
rules/fuzzy-matching are exhausted. **Which provider, and whose API key, is
configurable per user** from **Settings → Categorisation**:

| Setting | Effect |
|---|---|
| Provider = Gemini | Unknown merchants are classified via the Gemini API |
| Provider = Claude | Unknown merchants are classified via the Claude (Anthropic) API |
| Provider = Off | No LLM is called; categorisation runs on rules + fuzzy matching only |

A user's own key (entered in Settings) takes precedence; if they haven't set one,
the system-wide `GEMINI_API_KEY` / `ANTHROPIC_API_KEY` from `.env` is used as a
fallback (useful for a self-hosted instance sharing one key across its own users).
API keys are **never returned by the API** once saved — Settings shows only a
masked preview (`sk-...ab12`), consistent with NFR-8.

Only the *normalised merchant string* (e.g. `"SWIGGY"`) is ever sent to whichever
provider is active — never amounts, account numbers, balances, or your identity
(NFR-10, enforced in code by `app/categorise/sanitiser.py`).

---

## Repository layout

```
backend/     FastAPI app + worker
  app/
    routers/       HTTP endpoints
    services/      Business logic (safe_to_spend, seed, auth, …)
    repositories/  MongoDB access layer
    models/        Pydantic / MongoDB document models
    categorise/    Rules → fuzzy → LLM pipeline + seed data (YAML)
    worker/        Async job runner
  scripts/
    create_demo_user.py  ← seed a demo account
frontend/    Next.js app (App Router)
  app/
    (auth)/        Login / register pages
    (app)/         Authenticated pages (dashboard, accounts, …)
  components/ui/   Design-system primitives (Card, Button, Badge, …)
docs/        REQUIREMENTS.md, TECHNICAL_DESIGN.md
docker-compose.yml
.env.example
```

---

## Running tests

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate
pip install -e ".[dev]"
pytest                      # unit tests run standalone; integration tests
                             # (testcontainers + real Mongo) skip automatically
                             # if Docker isn't available
```

The FR-8.4 worked example (the normative Safe-to-Spend test case from
`docs/REQUIREMENTS.md`) is asserted to the paise in
`backend/tests/unit/test_safe_to_spend.py`.

```bash
cd frontend
npm install
npm run typecheck
npm run build
```

---

## Regenerating frontend API types

`frontend/types/api.ts` is currently hand-written (bootstrapping). Once the API is
running, regenerate it from the live OpenAPI schema:

```bash
cd frontend
npm run generate-types
```

---

## Backup / restore

```bash
make backup                          # dumps to ./backups/<timestamp>/
make restore FILE=backups/<ts>/finance_tracker.archive
```

---

## Status against the spec

Backend implements the full data model and API surface in
`docs/TECHNICAL_DESIGN.md` sections 5 and 10: auth, CSV/XLSX/PDF statement
import with column-mapping fallback, merchant normalisation + idempotent
dedupe, the rules → fuzzy → LLM categorisation pipeline with per-merchant
caching and a monthly call budget, recurring-commitment detection, Safe-to-Spend
with a full waterfall explanation and version-based cache invalidation, wishlist
affordability + months-to-afford, goals with an auto-sized emergency fund,
variable-income allocation proposals, net worth, the plain-language monthly
advisor summary + anomaly detection (template-based, never LLM-computed —
FR-11.2), and CSV/JSON export.

Not yet built: OCR for scanned PDFs is stubbed behind `OCR_ENABLED` but not
wired to a specific OCR backend in this pass; AMFI NAV lookup (P2).

---

*This is a personal finance tracking tool. It is informational software and does
not provide regulated investment, tax, or legal advice.*
