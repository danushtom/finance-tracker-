# Finance Tracker — Technical Design Document

| Field | Value |
|---|---|
| Product | Finance Tracker |
| Version | 1.0 (draft) |
| Date | 18 August 2026 |
| Author | Dan |
| Status | Draft for build |
| Requirements | `REQUIREMENTS.md` (FR/NFR IDs referenced throughout) |

---

## 1. Scope of this document

This document describes **how** the system in `REQUIREMENTS.md` is built: architecture, data model, algorithms, API contracts, and the decisions behind them. Where a design element exists to satisfy a specific requirement, the requirement ID is cited.

The two hard architectural constraints are fixed up front (C-2): **FastAPI backend, MongoDB running locally, Next.js + TypeScript frontend.**

---

## 2. Architecture

### 2.1 High level

```
┌──────────────────────────────────────────────────────────────┐
│  Browser                                                     │
│  Next.js 15 (App Router) · TypeScript · Tailwind · shadcn/ui │
│  TanStack Query · Recharts · Zod                             │
└───────────────────────────┬──────────────────────────────────┘
                            │  HTTPS/JSON  (OpenAPI-generated client)
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  FastAPI (ASGI, uvicorn)                                     │
│                                                              │
│  routers/     thin HTTP layer, Pydantic in/out               │
│  services/    ALL business logic + money maths               │
│  repositories/ Mongo access, user_id scoping enforced here   │
│  parsers/     CSV · XLSX · PDF adapters                      │
│  categorise/  rules engine · fuzzy · LLM fallback            │
└─────────┬────────────────────────────────┬───────────────────┘
          │                                │
          ▼                                ▼
┌──────────────────────┐        ┌──────────────────────────────┐
│  MongoDB (local)     │        │  Worker process              │
│  single-node replSet │◀──────▶│  polls jobs collection       │
│  rs0 → transactions  │        │  parse → categorise → save   │
└──────────────────────┘        └───────────┬──────────────────┘
          ▲                                 │
          │                                 ▼
┌──────────────────────┐        ┌──────────────────────────────┐
│  Local file storage  │        │  Claude API (optional)       │
│  ./storage/uploads   │        │  merchant-name only (NFR-10) │
└──────────────────────┘        └──────────────────────────────┘
```

### 2.2 Layering rules (non-negotiable)

1. **Routers** contain no business logic. They validate input, call a service, shape the response.
2. **Services** own all computation. Every rupee-affecting calculation lives here and is unit tested (NFR-6).
3. **Repositories** are the only code that talks to Mongo. Every repository method takes `user_id` as its first argument and injects it into every filter (NFR-7). There is no repository method that can query without it.
4. The **LLM never computes.** It proposes a category label for a merchant string. It does not see amounts, does not produce numbers, and no number displayed to the user originates from it (FR-11.2, NFR-10).

### 2.3 Request/processing flow for an import

```
POST /imports (multipart)
   → validate size/type              (FR-2.2)
   → write file to ./storage/uploads/{user_id}/{import_id}{ext}
   → insert import doc  status=queued
   → insert job doc     type=process_import
   → 202 { import_id }

worker picks up job
   → detect format → select parser adapter
   → parse rows → RawRow[]
   → normalise → NormalisedTxn[]     (FR-3)
   → fingerprint + dedupe check      (FR-2.11)
   → categorise batch                (FR-4)
   → write transactions in a Mongo transaction
   → update import doc with summary  (FR-2.13)
   → invalidate derived-number cache (FR-8.3.6)

frontend polls GET /imports/{id} until terminal state
```

---

## 3. Technology choices

| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js 15 (App Router), TypeScript strict | Constraint C-2; server components for shells keep the client bundle small |
| Styling | Tailwind CSS + shadcn/ui | Copy-in components, no runtime dependency lock-in, accessible primitives (NFR-15) |
| Charts | Recharts | Composable, sensible defaults, adequate for the 4–5 chart types needed |
| Data fetching | TanStack Query | Cache invalidation on mutation is the mechanism behind FR-8.3.6 client-side |
| Forms/validation | react-hook-form + Zod | Zod schemas generated from the OpenAPI spec (NFR-18) |
| Backend | FastAPI + Pydantic v2 | Constraint C-2; OpenAPI generation drives frontend types for free |
| DB driver | Motor (async PyMongo) | Non-blocking under the ASGI loop |
| DB | MongoDB 7.x local, single-node replica set | Constraint C-1; replica set is **required** for multi-document transactions (NFR-12) |
| Auth | JWT access + rotating refresh, Argon2id hashing (`argon2-cffi`) | FR-1 |
| CSV/XLSX | pandas + openpyxl (xlsx), `csv` sniffer for delimiters | Robust header/type inference |
| PDF | pdfplumber primary, camelot fallback, pikepdf for decryption | FR-2.1, FR-2.4 |
| OCR | ocrmypdf + tesseract (optional, feature-flagged) | FR-2.8 |
| Fuzzy match | RapidFuzz | Fast C++ implementation of `token_set_ratio` |
| LLM | Claude API via `anthropic` SDK | FR-4.2; abstracted behind a `Categoriser` protocol so it can be swapped or disabled |
| Jobs | Mongo-backed job queue + dedicated worker process | Avoids adding Redis; keeps NFR-19 (`docker compose up`, no cloud) true |
| Testing | pytest + pytest-asyncio + testcontainers-mongo; Vitest + Playwright | NFR-6 |
| Packaging | Docker Compose: `mongo`, `api`, `worker`, `web` | NFR-19 |

**Rejected:** Celery/Redis (extra infra for a single-user local app), SQL + SQLAlchemy (constraint), Prisma/Mongoose (backend is Python), server-side LLM classification of every transaction (cost, latency, non-determinism — the entire point of FR-4.2).

---

## 4. Repository layout

```
finance-tracker/
├─ docs/
│  ├─ REQUIREMENTS.md
│  └─ TECHNICAL_DESIGN.md
├─ backend/
│  ├─ app/
│  │  ├─ main.py                  # app factory, middleware, router mount
│  │  ├─ config.py                # pydantic-settings, env only (NFR-8)
│  │  ├─ db.py                    # motor client, index bootstrap
│  │  ├─ deps.py                  # get_current_user, get_db
│  │  ├─ errors.py                # problem+json handlers
│  │  ├─ models/                  # Pydantic domain models (shared shapes)
│  │  ├─ schemas/                 # request/response DTOs
│  │  ├─ routers/
│  │  │  ├─ auth.py  accounts.py  imports.py  transactions.py
│  │  │  ├─ categories.py  rules.py  income.py  commitments.py
│  │  │  ├─ dashboard.py  goals.py  wishlist.py  investments.py
│  │  │  └─ settings.py  export.py
│  │  ├─ services/
│  │  │  ├─ import_service.py     # orchestrates parse→categorise→persist
│  │  │  ├─ normalise.py          # FR-3
│  │  │  ├─ dedupe.py             # FR-2.11
│  │  │  ├─ recurring.py          # FR-7.1
│  │  │  ├─ safe_to_spend.py      # FR-8.3  ← most tested file in the repo
│  │  │  ├─ advisor.py            # FR-11
│  │  │  ├─ allocation.py         # FR-12
│  │  │  ├─ affordability.py      # FR-9
│  │  │  └─ networth.py           # FR-13
│  │  ├─ parsers/
│  │  │  ├─ base.py               # StatementParser protocol
│  │  │  ├─ csv_parser.py  xlsx_parser.py  pdf_parser.py
│  │  │  ├─ column_map.py         # header detection + saved mappings
│  │  │  └─ money.py              # Indian number/date parsing
│  │  ├─ categorise/
│  │  │  ├─ engine.py             # ordered pipeline
│  │  │  ├─ rules.py              # matching
│  │  │  ├─ fuzzy.py
│  │  │  ├─ llm.py                # Claude client, batching, cache
│  │  │  ├─ sanitiser.py          # NFR-10 enforcement
│  │  │  └─ seed_rules.yaml       # FR-4.11
│  │  ├─ repositories/            # one file per collection
│  │  └─ worker/
│  │     ├─ runner.py             # poll loop
│  │     └─ handlers.py
│  ├─ tests/
│  │  ├─ unit/  integration/  fixtures/statements/
│  └─ pyproject.toml
├─ frontend/
│  ├─ app/
│  │  ├─ (auth)/login  (auth)/register
│  │  └─ (app)/dashboard  /transactions  /import  /review
│  │     /rules  /wishlist  /goals  /investments  /accounts  /settings
│  ├─ components/  lib/  hooks/  types/api.ts (generated)
│  └─ package.json
├─ docker-compose.yml
├─ .env.example
└─ Makefile
```

---

## 5. Data model

### 5.1 Conventions

- Every collection except `users` has `user_id: ObjectId` as the **first field of every index**.
- Every document has `created_at` and `updated_at` (UTC `datetime`).
- Money is stored as **`int` paise** in fields suffixed `_minor` (NFR-5). ₹1,450.50 → `145050`. Sign: outflow negative, inflow positive.
- Dates for transactions are stored as UTC midnight of the **local (Asia/Kolkata) calendar date**, so month bucketing never drifts across a timezone boundary (NFR-16).
- `schema_version: int` on every document to allow forward migration.

### 5.2 Collections

#### `users`
```jsonc
{
  _id, email,                       // lowercased, unique
  password_hash,                    // Argon2id  (FR-1.1)
  display_name,
  settings: {
    currency: "INR",
    timezone: "Asia/Kolkata",
    month_start_day: 1,             // Q-2 hook
    buffer_minor: 500000,           // ₹5,000  (FR-8.3)
    low_confidence_threshold: 70,   // FR-4.4
    monthly_savings_target_minor: 1500000,
    monthly_investment_target_minor: 1000000,
    variable_split: { invest_pct: 50, goals_pct: 30, discretionary_pct: 20 },  // FR-12.1
    count_expected_salary: true,    // FR-8.3.4
    llm_enabled: true,              // NFR-11
    llm_monthly_call_cap: 500       // FR-4.13
  },
  llm_calls_this_month: 0, llm_calls_month: "2026-08",
  created_at, updated_at, schema_version
}
```
Index: `{ email: 1 }` unique.

> `variable_split` percentages must sum to 100 — validated in the Pydantic model, not only in the UI.

#### `refresh_tokens`
```jsonc
{ _id, user_id, jti, token_hash, expires_at, revoked_at, user_agent, created_at }
```
Indexes: `{ user_id:1, jti:1 }` unique · `{ expires_at:1 }` TTL.

#### `accounts` (FR-13.1)
```jsonc
{
  _id, user_id, name, type,          // bank|cash|credit_card|brokerage|mf_folio|ppf_epf|asset|liability
  institution, last4,
  current_balance_minor, balance_as_of,
  is_asset: true,                    // false for credit_card / liability
  column_mapping: { ... } | null,    // saved CSV/XLSX mapping (FR-2.6)
  archived: false, created_at, updated_at
}
```
Index: `{ user_id:1, archived:1 }`.

#### `categories` (FR-5)
```jsonc
{
  _id, user_id, name, parent_id | null,
  class: "fixed"|"variable"|"isolated"|"income"|"transfer"|"investment",  // FR-5.2
  colour, icon, is_system: true, archived: false, sort_order,
  created_at, updated_at
}
```
Indexes: `{ user_id:1, archived:1, sort_order:1 }` · `{ user_id:1, parent_id:1 }`.

The **`class`** field — not the name — drives every calculation. Renaming "Food" to "Grub" must not change any number.

#### `merchants` — learned merchant memory
```jsonc
{
  _id, user_id, merchant_norm,       // canonical key
  display_name, category_id, subcategory_id,
  confidence, source: "user"|"llm"|"seed",
  txn_count, first_seen, last_seen, total_minor,
  created_at, updated_at
}
```
Index: `{ user_id:1, merchant_norm:1 }` unique.

This collection is both the cache that makes FR-4.2 true and the corpus for fuzzy matching.

#### `rules` (FR-4.6, FR-4.9, FR-4.10)
```jsonc
{
  _id, user_id,
  match_type: "exact"|"contains"|"starts_with"|"regex",
  pattern,                            // normalised merchant form
  direction: "debit"|"credit"|null,
  amount_min_minor: null, amount_max_minor: null,   // FR-4.10
  category_id, subcategory_id, kind_override: null,
  priority: 100,                      // higher wins; user rules seed at 1000
  source: "user"|"seed"|"llm_confirmed",
  enabled: true, hit_count: 0, last_hit_at,
  created_at, updated_at
}
```
Indexes: `{ user_id:1, enabled:1, priority:-1 }` · `{ user_id:1, match_type:1, pattern:1 }` unique partial where `match_type = "exact"`.

#### `imports` (FR-2.13)
```jsonc
{
  _id, user_id, account_id,
  filename, stored_path, mime, size_bytes, sha256,
  status: "queued"|"parsing"|"needs_mapping"|"categorising"|"needs_review"|"completed"|"failed",
  parser: "csv"|"xlsx"|"pdf"|"pdf_ocr",
  summary: {
    rows_found, imported, duplicates_skipped, failed,
    date_from, date_to,
    opening_balance_minor, closing_balance_minor,
    llm_calls, needs_review_count
  },
  errors: [ { row, reason } ],
  preview: [ /* first 10 parsed rows for the mapping screen */ ],
  started_at, finished_at, created_at
}
```
Index: `{ user_id:1, created_at:-1 }`.

#### `transactions` — the core collection
```jsonc
{
  _id, user_id, account_id, import_id | null,
  date,                               // UTC midnight of local date
  description_raw,                    // verbatim, never mutated (FR-3.1)
  merchant_norm, merchant_id | null,
  counterparty_vpa | null,            // FR-3.4
  amount_minor,                       // signed (NFR-5)
  direction: "debit"|"credit",
  balance_minor | null,
  kind: "expense"|"income"|"transfer"|"investment"|"refund",   // FR-3.3
  category_id, subcategory_id | null,
  category_class,                     // denormalised from category for fast aggregation
  income_source_id | null,            // FR-6.2
  confidence: 0-100,                  // FR-4.3
  categorised_by: "rule"|"fuzzy"|"llm"|"user"|"none",
  needs_review: false,                // FR-4.4
  is_recurring: false, commitment_id | null,
  transfer_pair_id | null,            // FR-3.5
  refund_of_id | null,                // FR-3.6
  fingerprint,                        // FR-2.11
  tags: [], note | null,
  is_manual: false,                   // FR-2.15
  created_at, updated_at, schema_version
}
```

Indexes:

| Index | Serves |
|---|---|
| `{ user_id:1, date:-1 }` | transaction list, month queries |
| `{ user_id:1, fingerprint:1 }` **unique** | FR-2.11 dedupe — enforced by the DB, not just by code |
| `{ user_id:1, date:-1, category_class:1 }` | Safe-to-Spend aggregation (FR-8.3) |
| `{ user_id:1, category_id:1, date:-1 }` | category drill-down |
| `{ user_id:1, merchant_norm:1, date:-1 }` | merchant history, recurring detection |
| `{ user_id:1, needs_review:1, date:-1 }` | review queue (FR-15) |
| `{ user_id:1, account_id:1, date:-1 }` | per-account views |
| `{ user_id:1, import_id:1 }` | delete-an-import (FR-2.14) |
| `{ user_id:1, description_raw:"text" }` | search |

#### `income_sources` (FR-6.1)
```jsonc
{
  _id, user_id, name, type: "baseline"|"variable",
  expected_amount_minor | null, cadence: "monthly"|"irregular",
  expected_day_of_month | null,
  match_patterns: [ "SALARY", "ACME PVT LTD" ],
  active: true, created_at, updated_at
}
```

#### `commitments` — confirmed recurring fixed expenses (FR-7.3)
```jsonc
{
  _id, user_id, merchant_norm, display_name, category_id,
  expected_amount_minor, cadence: "monthly"|"weekly"|"quarterly"|"yearly",
  day_of_month | null, next_expected_date,
  status: "detected"|"confirmed"|"cancelled",     // FR-7.2, FR-7.6
  amount_history: [ { date, amount_minor } ],     // FR-7.5
  created_at, updated_at
}
```
Index: `{ user_id:1, status:1, next_expected_date:1 }`.

#### `goals` (FR-10)
```jsonc
{
  _id, user_id, name, target_amount_minor, current_amount_minor,
  target_date | null, priority: "high"|"medium"|"low",
  linked_account_id | null,
  monthly_reservation_minor: 0,     // FR-10.7 → feeds Safe-to-Spend
  is_emergency_fund: false,         // FR-10.6
  contributions: [ { date, amount_minor, transaction_id | null } ],
  status: "active"|"achieved"|"archived",
  created_at, updated_at
}
```

#### `wishlist_items` (FR-9)
```jsonc
{
  _id, user_id, name, price_minor,
  priority: "high"|"medium"|"low",
  target_month | null,              // "2026-09"
  url | null, note | null,
  status: "wanted"|"purchased"|"dropped",
  purchased_transaction_id | null,  // FR-9.7
  goal_id | null,                   // FR-9.6
  created_at, updated_at
}
```

#### `investments` (FR-14.1)
```jsonc
{
  _id, user_id, name,
  type: "index_fund"|"active_fund"|"debt"|"stock"|"gold"|"fd"|"epf_ppf"|"other",
  invested_minor, current_value_minor, units | null,
  identifier | null,                // AMFI scheme code / ticker (FR-14.6 hook)
  value_as_of, notes, archived: false, created_at, updated_at
}
```

#### `net_worth_snapshots` (FR-13.4)
```jsonc
{ _id, user_id, month: "2026-08",
  assets_minor, liabilities_minor, net_worth_minor,
  breakdown: [ { account_id, type, value_minor } ], created_at }
```
Index: `{ user_id:1, month:-1 }` unique.

#### `llm_cache` (FR-4.2)
```jsonc
{ _id, user_id, merchant_norm, category_id, confidence,
  model, prompt_version, created_at }
```
Index: `{ user_id:1, merchant_norm:1, prompt_version:1 }` unique.

#### `jobs`
```jsonc
{
  _id, user_id, type: "process_import"|"backfill_rule"|"detect_recurring"|"snapshot_networth",
  payload: {...},
  status: "queued"|"running"|"done"|"failed",
  attempts: 0, max_attempts: 3,
  locked_by | null, locked_at | null,     // worker lease
  error | null, created_at, updated_at
}
```
Indexes: `{ status:1, created_at:1 }` · `{ locked_at:1 }`.

#### `derived_cache` (FR-8.3.6)
```jsonc
{ _id, user_id, key: "sts:2026-08", version, payload: {...}, computed_at }
```
Index: `{ user_id:1, key:1 }` unique. `version` is bumped on any mutating write for that user; a cache entry whose `version` is behind the user's current `data_version` is ignored.

### 5.3 Transactions (ACID) usage

Multi-document transactions are used for exactly three operations, which is why the local Mongo must be a replica set (C-1):

1. **Import commit** — insert N transactions + update the import summary + bump `data_version`, atomically (NFR-12).
2. **Delete import** — remove its transactions + delete the import doc (FR-2.14).
3. **Category merge** — reassign transactions + rules + delete the category (FR-5.6).

Local setup:
```bash
mongod --replSet rs0 --dbpath ./data
mongosh --eval 'rs.initiate()'
```
Compose does this via a one-shot init container.

---

## 6. Money and dates

```python
# app/parsers/money.py
Paise = int  # the ONLY currency type in the backend

def to_minor(s: str) -> Paise:
    """'1,43,000.50' | '1,450.00 Cr' | '(2,000.00)' -> signed paise"""
```

Rules (NFR-5):

- Parse with `Decimal`, quantize to 2dp, multiply by 100, `int()`. **Never `float`.**
- Sum, subtract and compare in `int`. Divide only for display, or with explicit `//` + remainder handling for allocations.
- **Allocation splits must not lose paise.** `split_minor(amount, [50,30,20])` assigns floor shares and gives the remainder to the largest share. Unit tested with `sum(parts) == amount` for a wide range of inputs.
- The frontend receives integers and formats with a single helper:
  ```ts
  export const formatINR = (minor: number) =>
    new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR',
      maximumFractionDigits: 0 }).format(minor / 100);
  ```
  Division happens **only** inside this formatter. No arithmetic on rupee floats anywhere in the client.

Dates: parsed with an explicit format list, day-first preference, then localised to Asia/Kolkata and stored as UTC midnight of that local date (FR-2.9, NFR-16). Month keys are `"YYYY-MM"` strings computed in local time.

---

## 7. Ingestion pipeline

### 7.1 Parser protocol

```python
class StatementParser(Protocol):
    def sniff(self, path: Path) -> float: ...          # 0-1 confidence it can handle this file
    def preview(self, path: Path, *, password: str | None) -> Preview: ...
    def parse(self, path: Path, *, mapping: ColumnMapping | None,
              password: str | None) -> Iterator[RawRow]: ...

@dataclass
class RawRow:
    date: str; description: str
    debit: str | None; credit: str | None
    amount: str | None; balance: str | None
    ref: str | None; row_index: int
```

Selection: by extension first, then `sniff()`. A password-protected PDF is decrypted in memory with `pikepdf`; **the password is never written to disk, to the import document, or to logs** (FR-2.4, NFR-17).

### 7.2 CSV / XLSX (FR-2.6)

1. Read the first 30 rows raw.
2. Score each row as a candidate header by counting fuzzy matches against a synonym table:
   `date|txn date|value date|transaction date` · `description|narration|particulars|remarks|details` · `debit|withdrawal|withdrawal amt|dr` · `credit|deposit|deposit amt|cr` · `amount` · `balance|closing balance` · `ref|cheque no|utr`.
3. Best-scoring row above threshold becomes the header; everything above it is discarded (bank statements are full of preamble).
4. If no row scores above threshold → status `needs_mapping`, return `preview` and let the user map columns; the mapping is saved to `accounts.column_mapping` and reused (FR-2.6).
5. Separate debit/credit columns → sign derived from which is populated. Single amount column → sign from the value, or from a `Cr`/`Dr` suffix.

### 7.3 PDF (FR-2.7, FR-2.8)

1. `pdfplumber.extract_tables()` per page with tuned settings; concatenate, dropping repeated header rows.
2. If tables are empty or malformed → `camelot` in `stream` mode.
3. If extracted text length ≈ 0 across pages, the PDF is scanned → if OCR is enabled, run `ocrmypdf` then retry; every resulting transaction is flagged `needs_review = true` and the import is marked `pdf_ocr` (FR-2.8).
4. If still unparseable → `needs_mapping` with a text preview. **The parser never guesses silently** (FR-2.7).

Multi-line descriptions are joined when a row has a description fragment but no date/amount.

### 7.4 Normalisation (FR-3.1)

```
"UPI/DR/451233098711/SWIGGY/HDFC/swiggyupi@axis/Payment from Ph"
        → strip rails prefix  (UPI|IMPS|NEFT|RTGS|POS|ATM|ACH|MMT|CMS/…)
        → strip digit runs ≥4, dates, times, terminal ids, ref numbers
        → extract VPA → counterparty_vpa
        → uppercase, collapse whitespace, strip punctuation
        → "SWIGGY"
```
Implemented as an ordered list of named regex steps, each independently unit tested against a fixture corpus of real (anonymised) descriptions.

### 7.5 Deduplication (FR-2.11)

```python
fingerprint = sha256(f"{account_id}|{date:%Y-%m-%d}|{amount_minor}|"
                     f"{merchant_norm}|{balance_minor or ''}").hexdigest()
```
Enforced by the **unique index** `{user_id, fingerprint}` — insertion uses `ordered=False` bulk write and counts `E11000` errors as duplicates skipped. Correctness does not depend on an application-level check winning a race.

Genuine same-day same-amount repeats (two ₹200 coffees) differ by `balance_minor`; when balance is absent, a monotonic `occurrence_index` for identical keys within a single file is appended to the fingerprint.

---

## 8. Categorisation engine

### 8.1 Pipeline (FR-4.1)

Evaluated per distinct `merchant_norm`, not per transaction:

| # | Stage | Confidence | `categorised_by` |
|---|---|---|---|
| 1 | Exact **user** rule (hash-map lookup) | 100 | `rule` |
| 2 | Merchant memory, `source = "user"` | 98 | `user` |
| 3 | Pattern user rule (contains / starts_with / regex, priority order) | 95 | `rule` |
| 4 | Seed rule pack (FR-4.11) | 90 | `rule` |
| 5 | Merchant memory, `source = "llm"` (cache hit) | stored | `llm` |
| 6 | Fuzzy match vs. merchant memory, `token_set_ratio ≥ 88` | `min(88, score)` | `fuzzy` |
| 7 | LLM fallback (batched) | `min(85, model_confidence)` | `llm` |
| 8 | Nothing matched | 0 → `Uncategorised` | `none` |

`needs_review = confidence < user.settings.low_confidence_threshold` (FR-4.4).

Amount-conditional rules (FR-4.10) are evaluated per transaction after the merchant-level result, and can override it.

Rules are loaded once per import into an in-memory `RuleSet` (exact rules in a dict, patterns in a priority-sorted list). Typical volume is under 500 rules; no per-transaction DB round-trip.

### 8.2 LLM fallback contract (FR-4.2, NFR-10)

- Input is **only** the normalised merchant string. The sanitiser runs immediately before the API call and asserts: no digit run ≥4, no `@`, no currency symbol, no substring of the raw description beyond the merchant token, length ≤ 64. A failed assertion drops the merchant to `Uncategorised` rather than sending it.
- Merchants are **deduplicated and batched**, up to 40 per request.
- `temperature = 0`, `max_tokens` bounded, JSON-only response, `prompt_version` recorded so a prompt change can invalidate the cache deliberately.
- The response is validated against the user's allowed category list; anything unrecognised becomes `Uncategorised` with confidence 0.
- Results are written to `llm_cache` and `merchants`, so a merchant is classified **once, ever** (G-2).
- Timeout 30s, 2 retries with exponential backoff; on failure the batch degrades to `Uncategorised` and the import still completes (FR-4.12).
- `llm_calls_this_month` is incremented atomically and checked against `llm_monthly_call_cap` (FR-4.13). If `llm_enabled` is false, stage 7 is skipped entirely (NFR-11).

Prompt shape (`prompt_version = "v1"`):

```
You are classifying merchant names from Indian bank statements.
Allowed categories: <id:name list>
For each merchant, return the single best category id and a confidence 0-100.
If unsure, return "uncategorised" with a low confidence. Do not invent categories.
Merchants: ["SWIGGY", "CLAUDE AI", "ABC ENTERPRISES", ...]
Return JSON: [{"merchant": "...", "category_id": "...", "confidence": 0-100}]
```

### 8.3 Learning from correction (FR-4.6 – FR-4.8)

```
PATCH /transactions/{id}  { category_id }
   → update transaction, confidence = 100, categorised_by = "user", needs_review = false
   → upsert merchants entry with source = "user"
   → response includes rule_suggestion:
       { match_type: "exact", pattern: "CLAUDE AI",
         affected_past_count: 14, affected_future: true }

POST /rules  { ..., backfill: true }
   → create rule (priority 1000, source "user")
   → enqueue backfill_rule job
   → job recategorises matching transactions where categorised_by != "user"
```

**User-set categories are never overwritten by a rule, the LLM, or a backfill** (FR-4.7). The backfill preview count (FR-4.8) is computed with the same matcher the job will use, so the preview cannot disagree with the result.

### 8.4 Recurring detection (FR-7.1)

For each `merchant_norm` with ≥2 debits in the last 12 months: sort dates, compute deltas, and if the median delta falls within a cadence window (28–31, 7, 88–92, 360–370 days) with low variance, and amounts are within ±15% of their median → emit a **candidate** commitment with `status = "detected"`. Candidates are surfaced for confirmation and are **not** counted as committed until confirmed (FR-7.2).

---

## 9. Derived numbers

All of section 9 lives in `services/` and is the most heavily tested code in the project (NFR-6).

### 9.1 Safe-to-Spend (FR-8.3)

```python
def compute_safe_to_spend(user: User, month: str, today: date) -> SafeToSpend:
    s = user.settings

    baseline = sum_income(month, type="baseline")
    if baseline == 0 and s.count_expected_salary:
        baseline, baseline_is_expected = expected_baseline(month), True   # FR-8.3.4

    variable_received = sum_income(month, type="variable")                # FR-8.3.3
    discretionary = pct(variable_received, s.variable_split.discretionary_pct)

    spendable = baseline + discretionary

    fixed_due   = sum(c.expected_amount_minor for c in confirmed_commitments(month))
    fixed_paid  = sum_outflows(month, class_="fixed")
    fixed_left  = max(0, fixed_due - fixed_paid)                          # FR-7.4

    variable_spent = sum_outflows(month, class_in=("variable", "isolated"))
    # transfers and investments are excluded by class                     # FR-8.3.2

    savings_left    = max(0, s.monthly_savings_target_minor    - saved_this_month(month))
    investment_left = max(0, s.monthly_investment_target_minor - invested_this_month(month))
    goals_left      = sum(max(0, g.monthly_reservation_minor - funded(g, month))
                          for g in active_goals())                        # FR-10.7

    amount = (spendable - fixed_left - variable_spent
              - savings_left - investment_left - goals_left - s.buffer_minor)

    days_left = days_remaining_in_month(month, today)
    return SafeToSpend(
        amount_minor = amount,                       # may be negative internally
        is_over      = amount < 0,                   # FR-8.3.1 (UI floors at 0)
        per_day_minor = amount // days_left if days_left > 0 and amount > 0 else None,
        lines = [...],                               # the waterfall (FR-8.2)
    )
```

**Waterfall (FR-8.2).** Every `line` is `{ label, amount_minor, sign, drilldown }`, where `drilldown` is a transaction-query descriptor the frontend turns into a link. This makes every rupee traceable — the requirement that "no number in this product may be unexplainable".

**Verification.** The FR-8.4 worked example is a mandatory test:

```
(9_300_000 + 1_000_000) − 250_000 − 4_200_000 − 1_500_000 − 1_000_000 − 0 − 500_000
= 2_850_000 paise = ₹28,500          ✅
```

### 9.2 Aggregation queries

Month totals come from a single aggregation, not N queries:

```js
[ { $match: { user_id, date: { $gte: start, $lt: end }, kind: { $in: ["expense","refund"] } } },
  { $group: { _id: { cls: "$category_class", cat: "$category_id" },
              total: { $sum: "$amount_minor" }, count: { $sum: 1 } } } ]
```
Backed by `{ user_id:1, date:-1, category_class:1 }`. This satisfies NFR-3 (<300 ms) for a month of a few thousand transactions.

### 9.3 Caching and invalidation (FR-8.3.6)

`users.data_version` is incremented on every mutating write (import commit, category change, rule change, settings change, goal contribution). `derived_cache` entries store the `version` they were computed at; a stale version is a miss. There is no TTL-based staleness — correctness of the headline number is not left to a timer.

Client side, TanStack Query invalidates `['dashboard', month]` on every mutation.

### 9.4 Affordability (FR-9.2, FR-9.4)

```python
sts = safe_to_spend(month).amount_minor
affordable = item.price_minor <= sts
shortfall  = max(0, item.price_minor - sts)

surplus = baseline_income - median_fixed_3m - median_variable_3m      # FR-9.4
months_to_afford = ceil(shortfall / surplus) if surplus > 0 else None # → "not on current cash flow"
```
Each item is evaluated independently against the same `sts` snapshot (FR-9.3).

### 9.5 Advisor (FR-11)

```python
recommended_allocation = floor_to_500(
    max(0, baseline_income - median_fixed_3m - median_variable_3m - buffer))   # FR-11.3
```
Requires ≥2 complete months of data, else returns `insufficient_data` with what is known (FR-11.4). The plain-language sentence is produced by a **template with computed values substituted** — the LLM is not in this path at all (FR-11.2).

Anomaly detectors (FR-11.6), each a pure function over aggregates: category >150% of 3-month median · new recurring merchant · commitment price increase >10% · single transaction >3× the 90th-percentile transaction for its category.

### 9.6 Variable income allocation (FR-12)

On detecting a credit matched to a `variable` income source, create an allocation proposal using `split_minor(amount, [invest, goals, discretionary])` with paise-exact remainder handling. Only the discretionary slice reaches Safe-to-Spend (FR-12.2). The proposal is stored so plan-vs-actual can be compared later (FR-12.4).

---

## 10. API design

Base path `/api/v1`. All responses JSON. Errors use **RFC 9457 problem+json**:

```jsonc
{ "type": "/errors/validation", "title": "Invalid column mapping",
  "status": 422, "detail": "...", "instance": "/api/v1/imports/66f...",
  "errors": [ { "field": "mapping.date", "message": "required" } ] }
```

All money fields in requests and responses are integer paise, named `*_minor`.

### 10.1 Auth (FR-1)

| Method | Path | Notes |
|---|---|---|
| POST | `/auth/register` | email, password, optional invite code (FR-1.8) |
| POST | `/auth/login` | → access token (JSON) + refresh token (httpOnly, Secure, SameSite=Lax cookie) |
| POST | `/auth/refresh` | rotates the refresh token; reuse of a revoked token revokes the whole family |
| POST | `/auth/logout` | revokes current refresh token |
| GET | `/auth/me` | current user + settings |
| POST | `/auth/change-password` | revokes all refresh tokens (FR-1.5) |
| DELETE | `/auth/me` | hard-deletes the user and all their data (FR-1.6) |

Access token: 15 min, HS256, claims `sub`, `jti`, `exp`, `iat`. Refresh: 30 days, rotating, stored hashed.

### 10.2 Accounts, imports, transactions

| Method | Path | Notes |
|---|---|---|
| GET/POST | `/accounts` | list / create (FR-13.1) |
| PATCH/DELETE | `/accounts/{id}` | update balance, archive |
| POST | `/imports` | multipart: `file`, `account_id`, optional `password` → `202 {import_id}` (FR-2.5) |
| GET | `/imports` | history |
| GET | `/imports/{id}` | status + summary + preview (FR-2.13) |
| POST | `/imports/{id}/mapping` | submit column mapping, resume job (FR-2.6) |
| POST | `/imports/{id}/retry` | (NFR-12) |
| DELETE | `/imports/{id}` | removes exactly its transactions (FR-2.14) |
| GET | `/transactions` | filters: `month`, `from`, `to`, `account_id`, `category_id`, `class`, `kind`, `needs_review`, `min_minor`, `max_minor`, `q`; cursor pagination, `limit ≤ 200` |
| POST | `/transactions` | manual entry (FR-2.15) |
| PATCH | `/transactions/{id}` | category / kind / note / tags; returns `rule_suggestion` (FR-4.6) |
| POST | `/transactions/bulk-categorise` | `{ transaction_ids[], category_id }` (FR-15.3) |
| POST | `/transactions/{id}/split` | split a cash withdrawal (FR-5.7) |
| GET | `/transactions/review` | the review queue (FR-15.1) |

### 10.3 Categories and rules

| Method | Path | Notes |
|---|---|---|
| GET/POST | `/categories` | tree with `class` (FR-5) |
| PATCH/DELETE | `/categories/{id}` | rename, re-class, archive |
| POST | `/categories/{id}/merge` | `{ into_id }`, transactional (FR-5.6) |
| GET/POST | `/rules` | list / create with `backfill: bool` (FR-4.8) |
| POST | `/rules/preview` | → `{ affected_count, sample[] }` |
| PATCH/DELETE | `/rules/{id}` | edit, enable, reorder (FR-4.9) |
| GET | `/merchants` | learned memory, searchable |

### 10.4 Money model

| Method | Path | Notes |
|---|---|---|
| GET/POST/PATCH | `/income-sources` | FR-6.1 |
| GET | `/income?month=` | baseline vs variable breakdown (FR-6.4) |
| POST | `/income/{txn_id}/classify` | `{ source_id | type }` (FR-6.2) |
| GET | `/commitments` | `status` filter (FR-7) |
| POST | `/commitments/detect` | enqueue detection |
| PATCH | `/commitments/{id}` | confirm / cancel / adjust |
| GET | `/allocations?month=` | variable-income proposals (FR-12) |
| PATCH | `/allocations/{id}` | override split (FR-12.3) |

### 10.5 Dashboard and planning

| Method | Path | Response |
|---|---|---|
| GET | `/dashboard?month=YYYY-MM` | income block, four tiles, safe-to-spend, isolated tile, commitments, category breakdown, review count, top goals — one call, one payload (NFR-1) |
| GET | `/safe-to-spend?month=` | `{ amount_minor, is_over, per_day_minor, days_left, lines[] }` (FR-8.2) |
| GET/POST | `/wishlist` | items with live verdicts (FR-9.2) |
| POST | `/wishlist/simulate` | `{ item_ids[] }` → combined verdict (FR-9.5) |
| POST | `/wishlist/{id}/promote` | → goal (FR-9.6) |
| GET/POST | `/goals` | FR-10 |
| POST | `/goals/{id}/contribute` | FR-10.3 |
| GET | `/advisor/summary?month=` | plain-language summary + figures (FR-11.1) |
| GET | `/advisor/anomalies?month=` | FR-11.6 |
| GET/POST/PATCH | `/investments` | FR-14 |
| GET | `/net-worth` | current + trend (FR-13.3) |
| GET/PATCH | `/settings` | FR-11.5 |
| GET | `/export/transactions.csv` | FR-16.2 |
| GET | `/export/all.json` | FR-16.3 |

### 10.6 Contract example — `GET /safe-to-spend`

```jsonc
{
  "month": "2026-08",
  "amount_minor": 2850000,
  "is_over": false,
  "per_day_minor": 285000,
  "days_left": 10,
  "lines": [
    { "label": "Baseline income",            "amount_minor":  9300000, "sign": "+", "drilldown": {"kind":"income","source_type":"baseline"} },
    { "label": "Project income (20% share)", "amount_minor":  1000000, "sign": "+", "drilldown": {"kind":"income","source_type":"variable"} },
    { "label": "Fixed still due",            "amount_minor":   250000, "sign": "-", "drilldown": {"class":"fixed","unpaid":true} },
    { "label": "Spent so far",               "amount_minor":  4200000, "sign": "-", "drilldown": {"class":["variable","isolated"]} },
    { "label": "Savings not yet moved",      "amount_minor":  1500000, "sign": "-", "drilldown": null },
    { "label": "Investing not yet moved",    "amount_minor":  1000000, "sign": "-", "drilldown": null },
    { "label": "Buffer",                     "amount_minor":   500000, "sign": "-", "drilldown": null }
  ]
}
```

---

## 11. Frontend design

### 11.1 Routes

```
/login  /register
/dashboard        — FR-8.1, the hero screen
/transactions     — virtualised table, filters, inline category edit
/import           — upload, column mapping, job progress, summary
/review           — keyboard-driven triage (FR-15.2)
/rules            — rules + learned merchants
/wishlist         — affordability cards
/goals            — progress + contributions
/investments      — holdings, allocation, staged investing view
/accounts         — accounts + net worth
/settings         — rules, buffer, splits, LLM toggle, export, delete account
```

### 11.2 Component notes

- **`<SafeToSpendHero>`** — largest element on the dashboard. Shows the number, the per-day figure, and an "explain this number" button opening `<WaterfallSheet>` built from `lines[]`. When `is_over` is true it renders `₹0` with a secondary "over by ₹X" (FR-8.3.1).
- **`<IsolatedSpendTile>`** — Cigarettes and Alcohol, amount + trend arrow, neutral copy only (FR-5.5). Trend uses an arrow glyph **and** a text label, never colour alone (NFR-15).
- **`<AffordabilityCard>`** — ✅/❌ plus remaining Safe-to-Spend or shortfall and months-to-afford. The verdict is rendered as an icon **and** text.
- **`<ReviewQueue>`** — keyboard-first: `j/k` navigate, `1–9` assign frequent categories, `r` create rule, `enter` accept suggestion, `s` skip.
- **`<ColumnMapper>`** — shows the preview grid with dropdowns per column; persists the mapping to the account.
- **Charts** — Recharts. Category breakdown (bar, sorted desc), 6-month trend (line), net worth (area), allocation (donut). Categorical colours must be distinguishable in both themes and never the sole encoding of meaning.

### 11.3 State and types

- Server state via TanStack Query keyed `['dashboard', month]`, `['transactions', filters]`, `['safe-to-spend', month]`. Every mutation invalidates the derived keys — the client-side half of FR-8.3.6.
- API types generated from the FastAPI OpenAPI schema via `openapi-typescript` into `types/api.ts` (NFR-18). Hand-written duplicate interfaces are a review-blocking issue.
- Money handled as `number` (integer paise, safely within `Number.MAX_SAFE_INTEGER`) and only ever formatted through `formatINR` (NFR-5).
- Optimistic updates on category changes, with rollback on error.

---

## 12. Background worker

A single `worker` process polls `jobs`:

```python
job = await jobs.find_one_and_update(
    { "status": "queued", "$or": [{"locked_at": None},
                                  {"locked_at": {"$lt": now - LEASE}}] },
    { "$set": {"status": "running", "locked_by": WORKER_ID, "locked_at": now},
      "$inc": {"attempts": 1} },
    sort=[("created_at", 1)], return_document=AFTER)
```

Lease-based locking makes a crashed worker's job reclaimable. `attempts > max_attempts` → `failed`, surfaced in the UI with a retry action (NFR-12). Handlers: `process_import`, `backfill_rule`, `detect_recurring`, `snapshot_networth` (monthly, first run of a new month).

Chosen over Celery/ARQ specifically to avoid a Redis dependency and keep NFR-19 true: `docker compose up` and nothing else.

---

## 13. Security

| Concern | Design |
|---|---|
| Password storage | Argon2id, per-password salt, tuned params (FR-1.1) |
| Tokens | Short access token in memory (not `localStorage`); refresh in httpOnly Secure SameSite=Lax cookie; rotation with reuse detection |
| Tenant isolation | `user_id` injected at the repository layer; an integration test hits **every** endpoint as user B with user A's resource IDs and asserts 404 (NFR-7) |
| Upload safety | Extension + magic-byte check, 20 MB cap, files stored outside the web root under `storage/uploads/{user_id}/`, random filenames, never served statically |
| Zip/PDF bombs | Page-count and decompressed-size caps before parsing |
| Regex rules | User regexes compiled with a length cap and evaluated under a timeout to avoid catastrophic backtracking |
| Secrets | `pydantic-settings` from env only; startup fails loudly if `JWT_SECRET` is missing or default (NFR-8) |
| Rate limiting | Per-IP on `/auth/*`, per-user on `/imports` |
| CORS | Explicit allowlist of the frontend origin; credentials enabled |
| LLM egress | Sanitiser + assertion before every outbound call; a kill switch in settings (NFR-10, NFR-11) |
| Logging | Structured JSON with request id; a log filter redacts anything matching money, account-number, or email patterns (NFR-17) |

---

## 14. Testing strategy (NFR-6)

**Unit (pytest)** — money parsing and `split_minor` remainder handling · description normalisation against a fixture corpus · fingerprinting · rule matching precedence · fuzzy thresholds · recurring detection · **`safe_to_spend` including the FR-8.4 worked example asserted to the paise** · affordability and months-to-afford · advisor allocation · the LLM sanitiser (property test: no output ever contains a 4+ digit run, `@`, or a currency symbol).

**Integration (testcontainers + real MongoDB)** — full import of golden statement files (CSV, XLSX, PDF, encrypted PDF, OCR PDF) asserting exact transaction counts and totals · idempotent re-import · overlapping-statement import · delete-import removing exactly its rows · category merge atomicity · **cross-user isolation across every endpoint**.

**Frontend** — Vitest for `formatINR`, waterfall assembly, affordability rendering; Playwright for register → import CSV → correct a category → create rule → see dashboard → check Safe-to-Spend.

**Fixtures** — anonymised real statements with names, account numbers and VPAs replaced but structure preserved, committed under `tests/fixtures/statements/`. **Q-1 blocks parser sign-off**: without real sample files from the target banks, the parser cannot be considered done.

Coverage gate: 85% lines on `services/`, and `safe_to_spend.py` at 100% branch coverage.

---

## 15. Configuration

`.env.example`:

```bash
MONGODB_URI=mongodb://localhost:27017/?replicaSet=rs0
MONGODB_DB=finance_tracker
JWT_SECRET=                      # required, no default; startup fails if empty
JWT_ACCESS_TTL_MIN=15
JWT_REFRESH_TTL_DAYS=30
STORAGE_DIR=./storage/uploads
MAX_UPLOAD_MB=20
REGISTRATION_INVITE_CODE=        # empty = open registration (FR-1.8)
ANTHROPIC_API_KEY=               # empty = LLM fallback disabled (NFR-11)
LLM_MODEL=claude-sonnet-4-5
LLM_MONTHLY_CALL_CAP=500
OCR_ENABLED=false
CORS_ORIGINS=http://localhost:3000
TZ=Asia/Kolkata
LOG_LEVEL=INFO
```

`docker-compose.yml` services: `mongo` (replSet `rs0` + one-shot `mongo-init` running `rs.initiate()`), `api`, `worker`, `web`. Index creation and seed data (default categories per FR-5.3, seed rules per FR-4.11) run idempotently on API startup.

---

## 16. Migrations

`schema_version` on every document plus a `migrations/` directory of numbered idempotent scripts run at startup. Rules: additive changes only where possible; a renamed field is written to both for one release before the old one is dropped; every migration is re-runnable without effect on already-migrated documents.

---

## 17. Build order (mapped to milestones)

| Milestone | Build |
|---|---|
| **M1** | Compose stack + Mongo replSet · auth + user scoping + isolation tests · accounts · CSV/XLSX parser + column mapper · normalisation + fingerprint dedupe · categories + seed rules · transactions list + manual edit |
| **M2** | PDF parser (+ encrypted, + optional OCR) · merchant memory · fuzzy stage · LLM fallback with sanitiser, batching, cache, budget guard · rule creation from correction + backfill job · review queue · rules screen |
| **M3** | Income sources + credit matching · recurring detection + confirmation · `safe_to_spend` service + waterfall + FR-8.4 test · dashboard with all tiles · derived cache + `data_version` invalidation |
| **M4** | Wishlist + affordability + months-to-afford · goals + reservations + emergency fund default · variable-income allocation proposals |
| **M5** | Advisor summary + anomalies · net worth + monthly snapshots · investments + staged investing view · CSV/JSON export · Playwright suite |

---

## 18. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| PDF statement layouts vary wildly between banks | High — the primary input path fails | Fail loudly to `needs_mapping` rather than producing wrong data (FR-2.7); build against real fixtures early (Q-1); CSV/XLSX is the reliable path and ships first in M1 |
| Merchant normalisation over-strips and collapses distinct merchants | Medium — wrong categories, wrong totals | Ordered, individually tested regex steps; keep `description_raw` verbatim so any mistake is recoverable without re-import |
| Safe-to-Spend produces a number the user doesn't believe | High — kills the core value | Mandatory waterfall explainability (FR-8.2); every line drills through to transactions |
| LLM misclassifies and the mistake is cached | Medium | Confidence cap of 85 on LLM results, review queue surfacing, user corrections always win and are never overwritten (FR-4.7) |
| Float creeping into money maths | High — silent wrong numbers | Integer paise everywhere, single formatting helper, property tests on split remainders (NFR-5) |
| Local Mongo not configured as a replica set | Medium — transactions unavailable, partial imports possible | Compose handles `rs.initiate()`; API startup check fails fast with a clear message if transactions are unsupported |
| Scope sprawl into investing features | Medium — M1–M3 never finish | FR-14.5 and NG-2 hold the line: no product recommendations, no price feeds in v1 |

---

## Appendix A — Decision record

| ID | Decision | Rationale | Rejected alternative |
|---|---|---|---|
| ADR-1 | Rules-first categorisation with an LLM only as fallback, cached per merchant | Deterministic, free, fast, and the user's corrections compound into permanent accuracy | Classifying every transaction with an LLM: expensive, slow, non-deterministic, and it forgets |
| ADR-2 | Money as integer paise everywhere | Float currency arithmetic silently corrupts totals | `Decimal` over the wire (JSON has no decimal type); floats (unsafe) |
| ADR-3 | `class` on the category, not the name, drives all maths | Users rename categories; behaviour must not change when they do | Hardcoding category names in the calculation |
| ADR-4 | Mongo-backed job queue rather than Celery/ARQ | No Redis, keeps `docker compose up` sufficient for a local self-hosted app | Celery + Redis; FastAPI BackgroundTasks (not durable across restarts) |
| ADR-5 | Version-based cache invalidation instead of TTL | The headline number must never be stale after a change | TTL caching |
| ADR-6 | Only the normalised merchant token is ever sent to the LLM | Financial data privacy is a product property, not a setting | Sending full descriptions with amounts for better accuracy |
| ADR-7 | Single-node replica set for local Mongo | Multi-document transactions are needed for atomic imports | Standalone mongod with application-level compensation |
| ADR-8 | Uniqueness enforced by a DB index, not application checks | Dedupe must survive concurrency and retries | Application-level "check then insert" |
| ADR-9 | Variable income excluded from Safe-to-Spend except its discretionary slice | The product's core thesis: project income accelerates goals, it does not raise the spending ceiling | Treating all income as one pool |

---

*This document describes a personal finance tracking tool. It is informational software and does not provide regulated investment, tax, or legal advice.*
