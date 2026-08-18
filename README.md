# Finance Tracker

A personal finance tracker that turns bank statements into a single, explainable
**Safe-to-Spend** number, separates baseline income from unreliable project income,
and tracks a wishlist/goals plan against real cash flow. See
[`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) and
[`docs/TECHNICAL_DESIGN.md`](docs/TECHNICAL_DESIGN.md) for the full spec this was
built from.

This is an early build: the backend (API + worker + data model) is functionally
complete against the spec below. The frontend is wired up end-to-end against the
real API but is intentionally **undesigned** — plain HTML/Tailwind layout only,
no visual design system yet. Design comes later once example designs are provided.

## Stack

- **Backend**: FastAPI + Motor (async MongoDB) + a Mongo-backed job queue/worker
- **Frontend**: Next.js 15 (App Router) + TypeScript strict + TanStack Query
- **Database**: MongoDB 7, single-node replica set (required for multi-document
  transactions — see `docs/TECHNICAL_DESIGN.md` ADR-7)
- **LLM categorisation fallback**: pluggable — **Gemini or Claude, chosen per user**
  (see [Configuring the LLM provider](#configuring-the-llm-provider) below). The app
  is fully usable with the LLM turned off entirely (rules-only categorisation).

## Quick start

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

Then:

```bash
docker compose up --build
```

This starts four services: `mongo` (with a one-shot `mongo-init` container that
runs `rs.initiate()`), `api`, `worker`, and `web`.

- Web app: http://localhost:3000
- API: http://localhost:8000/api/v1 (interactive docs at http://localhost:8000/docs)

Register an account from the web app (or `POST /api/v1/auth/register`) to get
started. If `REGISTRATION_INVITE_CODE` is set in `.env`, registration requires it
(FR-1.8 — keeps a self-hosted instance from being open to the internet by default).

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
(NFR-10, enforced in code by `app/categorise/sanitiser.py`, which has its own
property test).

## Repository layout

```
backend/     FastAPI app + worker (see backend/app/... — routers/services/repositories/parsers/categorise)
frontend/    Next.js app
docs/        REQUIREMENTS.md, TECHNICAL_DESIGN.md — the spec this was built from
docker-compose.yml
.env.example
```

## Running tests

```bash
cd backend
python -m venv .venv && .venv/Scripts/activate   # or source .venv/bin/activate
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

## Regenerating frontend API types

`frontend/types/api.ts` is currently hand-written (bootstrapping — see the note at
the top of that file). Once the API is running, regenerate it from the live
OpenAPI schema instead of hand-editing it further:

```bash
cd frontend
npm run generate-types
```

## Backup / restore

```bash
make backup                          # dumps to ./backups/<timestamp>/
make restore FILE=backups/<ts>/finance_tracker.archive
```

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
wired to a specific OCR backend in this pass; AMFI NAV lookup (P2); the
frontend's visual design (intentionally deferred).

---

*This is a personal finance tracking tool. It is informational software and does
not provide regulated investment, tax, or legal advice.*
