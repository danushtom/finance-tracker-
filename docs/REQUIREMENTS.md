# Finance Tracker — Requirements Document

| Field | Value |
|---|---|
| Product | Finance Tracker (working name) |
| Version | 1.0 (draft) |
| Date | 18 August 2026 |
| Owner | Dan |
| Status | Draft for build |
| Related | `TECHNICAL_DESIGN.md` |

---

## 1. Purpose

Most expense trackers answer the question *"where did my money go?"* — which is a report about the past and changes nothing.

This product answers a different question: **"how much can I spend right now without damaging my plan?"**

It does that by ingesting real bank statements, learning how to categorise them once (not repeatedly), separating money into kinds that behave differently (baseline vs. variable income; fixed vs. discretionary spending), and producing a single defensible number — **Safe-to-Spend** — plus an affordability check against the things the user actually wants to buy.

## 2. Problem statement

The target user has:

- A predictable salary (₹93,000/month) and unpredictable project income (₹0–₹50,000+/month).
- Recurring software/cloud/subscription costs that are easy to lose track of (Claude, AWS, Netflix, internet).
- Discretionary spending that fluctuates (food delivery, electronics, days out).
- Categories of spending they specifically want visibility into rather than buried in "Lifestyle" (cigarettes, liquor).
- A wishlist of purchases at different price points and priorities (bed, NVMe SSD, monitor, GPU).
- No structured savings/investment plan, and a risk of inflating lifestyle to match a good project month.

Existing tools fail on three axes: they treat all income as one pool, they require manual categorisation forever, and they report instead of advising.

## 3. Goals

| ID | Goal | Success measure |
|---|---|---|
| G-1 | Turn a raw bank statement into categorised transactions with minimal manual work | ≥85% of transactions auto-categorised correctly on the second statement upload |
| G-2 | Never ask the user to categorise the same merchant twice | 0 repeat prompts for a merchant with a confirmed rule |
| G-3 | Produce a single, trustworthy Safe-to-Spend number | Number is fully explainable — every rupee of the deduction is traceable to a line item in the UI |
| G-4 | Prevent lifestyle inflation from variable income | Project income is allocated by rule (invest/save/discretionary) before it appears as spendable |
| G-5 | Make wishlist purchases a decision, not an impulse | "Can I afford this?" answers Yes/No + remaining Safe-to-Spend + months-to-afford |
| G-6 | Give visibility into deliberately isolated categories | Cigarettes and liquor have their own dashboard tile with monthly trend |

## 4. Non-goals (v1)

- **NG-1** — No bank API / account aggregator integration (no AA, no screen-scraping). Statement upload only.
- **NG-2** — No stock picking, no buy/sell recommendations, no price feeds for individual securities.
- **NG-3** — No tax filing, capital gains computation, or ITR support.
- **NG-4** — No mobile native app. Responsive web only.
- **NG-5** — No shared/family accounts or splitting bills between people.
- **NG-6** — No credit score, loan marketplace, or any monetised referral surface.

## 5. Users and personas

**Primary persona — "The variable-income individual contributor"**
Salaried, technically literate, receives irregular freelance/project income, comfortable uploading files, wants control rather than automation-by-magic. Runs the app locally or on a personal server. Cares about privacy of financial data.

**System actors**

| Actor | Description |
|---|---|
| User | Authenticated human owner of the data |
| Parser | Backend component converting uploaded files into normalised transactions |
| Categoriser | Rules engine, with an LLM fallback for unknown merchants |
| Advisor | Component that computes Safe-to-Spend, allocations and recommendations |

## 6. Glossary — the money model

These definitions are normative. The whole product depends on them.

| Term | Definition |
|---|---|
| **Baseline income** | Recurring, dependable income the user may plan around. Salary. |
| **Variable income** | Non-dependable income: project/freelance payments, bonuses, refunds above a threshold. Never treated as available for lifestyle by default. |
| **Fixed expense** | A recurring, largely non-negotiable outflow with a predictable amount and cadence: rent/PG, internet, Netflix, Claude, AWS, insurance, EMIs. |
| **Variable expense** | Discretionary outflow the user controls month to month: food, shopping, electronics, days out. |
| **Isolated expense** | A variable expense the user has explicitly chosen to surface separately for visibility (cigarettes, liquor). Financially it is variable; presentationally it is its own tile. |
| **Transfer** | Movement between the user's own accounts (bank → savings, bank → brokerage). Not income, not expense. Must be excluded from spending totals. |
| **Investment outflow** | A transfer into an investment account/instrument. Reduces cash, does not reduce net worth. |
| **Committed** | Money already promised this month: unpaid fixed expenses, planned savings not yet moved, planned investments not yet moved, goal reservations. |
| **Safe-to-Spend** | Baseline income + discretionary share of variable income − committed − already-spent variable − buffer. See FR-8.3. |
| **Buffer** | A user-configured cushion (default ₹5,000) that is never part of Safe-to-Spend. |

---

## 7. Functional requirements

Priority: **P0** = required for v1 launch, **P1** = required for "complete" product, **P2** = later.

### FR-1 — Accounts, authentication and identity

| ID | Priority | Requirement |
|---|---|---|
| FR-1.1 | P0 | A user can register with email + password. Passwords are hashed with Argon2id; plaintext is never stored or logged. |
| FR-1.2 | P0 | A user can log in and receive a short-lived access token and a longer-lived refresh token. |
| FR-1.3 | P0 | Every document in every collection carries a `user_id`. Every query is scoped by `user_id` at the repository layer — no endpoint may read or write data across users. |
| FR-1.4 | P0 | A user can log out, invalidating the refresh token. |
| FR-1.5 | P1 | A user can change their password; doing so revokes all existing refresh tokens. |
| FR-1.6 | P1 | A user can permanently delete their account and all associated data (hard delete, single operation). |
| FR-1.7 | P2 | Optional TOTP two-factor authentication. |
| FR-1.8 | P0 | Registration may be restricted by an env-controlled allowlist or invite code, so a self-hosted instance is not open to the internet by default. |

### FR-2 — Statement ingestion

| ID | Priority | Requirement |
|---|---|---|
| FR-2.1 | P0 | The user can upload a bank statement in **CSV**, **XLS/XLSX**, or **PDF**. |
| FR-2.2 | P0 | Maximum file size 20 MB; maximum 20,000 transactions per file. Files exceeding this are rejected with a clear message. |
| FR-2.3 | P0 | The user selects (or creates) the **account** the statement belongs to before or during upload. |
| FR-2.4 | P0 | Password-protected PDFs are supported: the user may supply a password at upload time. The password is used in-memory only and never persisted. |
| FR-2.5 | P0 | Upload is processed asynchronously. The UI shows a job status (`queued → parsing → categorising → needs_review → completed / failed`) and does not block. |
| FR-2.6 | P0 | For CSV/XLSX, the system auto-detects the header row and maps columns to `date`, `description`, `debit`, `credit`, `amount`, `balance`, `ref`. Where detection is ambiguous, the user is shown a **column-mapping screen** and their mapping is saved per account for reuse. |
| FR-2.7 | P0 | For PDF, the system extracts tabular transaction rows. Where the layout is unrecognised, the job ends in a `needs_mapping` state with the extracted text preview, rather than silently producing garbage. |
| FR-2.8 | P1 | Scanned/image PDFs are detected and passed through OCR before parsing; the user is warned that accuracy is lower and all rows are flagged for review. |
| FR-2.9 | P0 | Date formats `DD/MM/YYYY`, `DD-MM-YYYY`, `DD-MMM-YY`, `YYYY-MM-DD` are all parsed correctly. Ambiguous dates default to **day-first** (Indian convention) and this assumption is shown to the user. |
| FR-2.10 | P0 | Indian number formatting (`1,43,000.00`), trailing `Cr`/`Dr` markers, and parenthesised negatives are parsed correctly. |
| FR-2.11 | P0 | **Idempotent re-upload:** uploading the same statement twice must not create duplicate transactions. Duplicates are detected by a fingerprint of (account, date, amount, normalised description, running balance) and reported as "N transactions skipped as duplicates". |
| FR-2.12 | P1 | Overlapping statements (e.g. Jan–Mar then Feb–Apr) are handled: only genuinely new transactions are added. |
| FR-2.13 | P0 | A parse run produces a summary: rows found, transactions imported, duplicates skipped, rows failed, date range covered, opening/closing balance. |
| FR-2.14 | P1 | The user can view, re-run, or delete a past import. Deleting an import removes exactly the transactions it created. |
| FR-2.15 | P1 | The user can add a transaction manually (for cash spending that never touches the bank). |

### FR-3 — Transaction normalisation

| ID | Priority | Requirement |
|---|---|---|
| FR-3.1 | P0 | Every transaction stores raw description verbatim **and** a normalised merchant string (uppercased, UPI/IMPS/NEFT prefixes, reference numbers, dates, and terminal IDs stripped). |
| FR-3.2 | P0 | Amounts are stored as **integer paise** (`amount_minor`), never as floats. Sign convention: outflow negative, inflow positive. |
| FR-3.3 | P0 | Each transaction has a `direction` (`debit`/`credit`) and a `kind` (`expense`, `income`, `transfer`, `investment`, `refund`). |
| FR-3.4 | P0 | UPI transactions are parsed to extract the counterparty VPA and payee name where present. |
| FR-3.5 | P1 | Transfers between the user's own registered accounts are auto-detected (matching amount, opposite direction, within 3 days) and linked as a transfer pair, excluded from spending. |
| FR-3.6 | P1 | Refunds/reversals are detected (credit matching a prior debit for the same merchant within 60 days) and offset against the original expense in reporting. |

### FR-4 — Categorisation

This is the core intelligence of the product. The sequence is: **rules → LLM fallback → user confirmation → new rule learned.**

| ID | Priority | Requirement |
|---|---|---|
| FR-4.1 | P0 | The system attempts categorisation in strict order: (1) exact merchant rule, (2) pattern/keyword rule, (3) fuzzy match against previously categorised merchants above a similarity threshold, (4) LLM fallback, (5) `Uncategorised`. |
| FR-4.2 | P0 | The LLM is invoked **only** for merchants unresolved by steps 1–3, is called once per **distinct merchant** (not per transaction), and results are cached. Re-uploading a statement must not re-invoke the LLM for already-known merchants. |
| FR-4.3 | P0 | Every transaction stores a `confidence` (0–100) and a `categorised_by` value (`rule`, `fuzzy`, `llm`, `user`, `none`). |
| FR-4.4 | P0 | Transactions with confidence below a threshold (default 70) are surfaced in a **Review queue** with the UI copy pattern: *"⚠️ We aren't sure about this one."* |
| FR-4.5 | P0 | The user can change the category of any transaction at any time. |
| FR-4.6 | P0 | When the user corrects a category, the system offers to create a rule: *"Always categorise CLAUDE.AI as Software?"* — with scope options: this transaction only / this merchant always / all merchants matching a pattern. |
| FR-4.7 | P0 | A user-created rule has higher precedence than any LLM or fuzzy result and is never overwritten automatically. |
| FR-4.8 | P0 | Applying a new rule offers to **backfill** — retroactively recategorise past transactions matching it, with a preview of how many will change. |
| FR-4.9 | P1 | Rules are manageable in a dedicated screen: list, search, edit, disable, delete, reorder priority. |
| FR-4.10 | P1 | Amount-conditional rules are supported (e.g. `AMAZON` under ₹1,000 → Household; over ₹5,000 → Electronics). |
| FR-4.11 | P0 | The system ships with a seed rule pack for common Indian merchants (Swiggy, Zomato, Blinkit, Zepto, BigBasket, Amazon, Flipkart, Myntra, Netflix, Spotify, Jio, Airtel, IRCTC, Uber, Ola, Rapido, HPCL/IOC/BP, AWS, GitHub, OpenAI, Anthropic/Claude, Google Cloud, ATM withdrawal patterns). |
| FR-4.12 | P1 | If the LLM is unavailable or the API key is absent, categorisation degrades gracefully to rules-only. The system must remain fully usable with the LLM disabled. |
| FR-4.13 | P1 | An LLM budget guard: a configurable monthly cap on LLM calls/spend, after which fallback is disabled and unknowns go to the review queue. |

### FR-5 — Category taxonomy

| ID | Priority | Requirement |
|---|---|---|
| FR-5.1 | P0 | Categories are two-level: category → subcategory. |
| FR-5.2 | P0 | Every category carries a **class**: `fixed`, `variable`, `isolated`, `income`, `transfer`, `investment`. This class drives the Safe-to-Spend maths, not the category name. |
| FR-5.3 | P0 | Default taxonomy ships with at least: Housing (Rent, Maintenance) · Utilities (Internet, Electricity, Mobile) · Subscriptions (Streaming, Music, News) · Software & AI (AI Tools, Dev Tools, Cloud) · Food (Groceries, Delivery, Dining Out) · Transport (Fuel, Cabs, Travel) · Shopping (Clothing, Electronics, Household) · Health (Medical, Fitness, Insurance) · Entertainment (Days Out, Games, Events) · **Cigarettes** · **Alcohol** · Cash Withdrawal · Fees & Charges · Gifts & Donations · Income (Salary, Project Income, Interest, Refunds) · Transfers · Investments (Mutual Funds, Stocks, Gold, PPF/EPF) · Uncategorised. |
| FR-5.4 | P0 | Cigarettes and Alcohol are class `isolated` by default and always render as their own dashboard tile with month-over-month trend. |
| FR-5.5 | P0 | The tone of isolated-category reporting is neutral and factual. No moralising copy, no warnings, no streak-shaming. It states the number and the trend. |
| FR-5.6 | P1 | The user can create, rename, merge, archive and re-class categories. Merging reassigns all transactions and rules. |
| FR-5.7 | P1 | Cash withdrawals can optionally be "split" by the user into categories after the fact, so ₹5,000 from an ATM does not disappear into a black hole. |

### FR-6 — Income

| ID | Priority | Requirement |
|---|---|---|
| FR-6.1 | P0 | Income sources are configured with a name, type (`baseline` / `variable`), expected amount, and expected cadence (monthly, day-of-month, or irregular). |
| FR-6.2 | P0 | Incoming credits are matched to configured income sources by rule; unmatched credits above a threshold prompt the user: *"Is this baseline or variable income?"* |
| FR-6.3 | P0 | Baseline income may be planned against. Variable income may **not** be planned against — no forecast, budget, or Safe-to-Spend calculation may assume variable income that has not actually been received. |
| FR-6.4 | P0 | The dashboard shows baseline and variable income as visually distinct figures, never as one merged "total income" headline alone. |
| FR-6.5 | P1 | The user sees a 12-month history of variable income with median and worst-month figures, to make its unreliability legible. |

### FR-7 — Fixed vs. variable commitments and recurring detection

| ID | Priority | Requirement |
|---|---|---|
| FR-7.1 | P0 | The system detects recurring transactions: same normalised merchant, similar amount (±15%), regular interval (28–31 / 7 / 90 / 365 days), at least 2 occurrences. |
| FR-7.2 | P0 | Detected recurring items are presented to the user for confirmation before being treated as fixed commitments. |
| FR-7.3 | P0 | A confirmed commitment stores expected amount, cadence, next expected date, and category. |
| FR-7.4 | P0 | The dashboard shows, for the current month: total fixed commitments, amount already paid, amount still due. |
| FR-7.5 | P1 | The system flags commitments that have changed in price (*"AWS is ₹1,450 this month, up from ₹980"*) and commitments that have not been charged when expected. |
| FR-7.6 | P1 | The user can mark a commitment as cancelled; it stops being counted as committed. |
| FR-7.7 | P1 | A "subscription audit" view lists all active subscriptions with annualised cost, sorted by cost, so unused spend is visible. |

### FR-8 — Dashboard and Safe-to-Spend

#### FR-8.1 — Dashboard content (P0)

The home screen, for the selected month, shows in this order:

1. **Month header** with month selector (default: current month).
2. **Income block** — baseline income and variable income shown separately, each with received/expected state, then the total.
3. **Four summary tiles** — Spent, Saved, Invested, Available.
4. **Safe-to-Spend hero** — the largest element on the page: the number, a per-day equivalent for the remaining days of the month, and an "explain this number" affordance.
5. **Isolated categories tile** — Cigarettes and Alcohol, month total and trend arrow.
6. **Fixed commitments** — due vs. paid, with a list.
7. **Spending by category** — bar or donut chart with drill-down to transactions.
8. **Review queue badge** — count of low-confidence transactions needing attention.
9. **Goals and wishlist snapshot** — top 3 by priority with progress.

#### FR-8.2 — Explainability (P0)

Tapping "explain this number" must show the full derivation as a line-by-line waterfall, every line linking to the underlying transactions. **No number in this product may be unexplainable.**

#### FR-8.3 — Safe-to-Spend definition (P0)

For a given month `M`, as of today:

```
  baseline_income_received            (credits matched to baseline sources in M)
+ discretionary_share_of_variable     (variable income received in M × discretionary_pct)
──────────────────────────────────────────────────────────────────────────────────
= spendable_pool

−  fixed_remaining                    (confirmed commitments due in M, minus those already paid)
−  variable_spent_to_date             (all class=variable and class=isolated outflows in M)
−  planned_savings_remaining          (monthly savings target − amount already transferred)
−  planned_investment_remaining       (monthly investing target − amount already invested)
−  goal_reservations_remaining        (this month's reservations for goals/wishlist not yet funded)
−  buffer                             (user-configured, default ₹5,000)
──────────────────────────────────────────────────────────────────────────────────
= SAFE-TO-SPEND
```

Rules governing this number:

- **FR-8.3.1** — Safe-to-Spend is floored at display level: if negative it is shown as **₹0 (over by ₹X)**, never as a negative headline.
- **FR-8.3.2** — Transfers and investment outflows are never counted as spending.
- **FR-8.3.3** — Only variable income **actually received** contributes. Expected-but-unreceived variable income contributes ₹0.
- **FR-8.3.4** — If baseline salary for the month has not yet been received but is expected, the user may choose (setting) whether to count it. Default: **count it**, with the tile marked "expected".
- **FR-8.3.5** — Per-day figure = Safe-to-Spend ÷ days remaining in the month (inclusive of today), shown only when ≥1 day remains.
- **FR-8.3.6** — Recomputed on demand and after any mutation (new import, category change, rule change, settings change). Cached with an explicit invalidation key; never served stale after a mutation.

#### FR-8.4 — Worked example (normative test case)

| Input | Value |
|---|---|
| Baseline income received | ₹93,000 |
| Variable income received | ₹50,000 |
| Variable allocation rule | 50% invest / 30% goals / 20% discretionary |
| Discretionary share of variable | ₹10,000 |
| Fixed commitments for month | ₹18,000 |
| Fixed already paid | ₹15,500 |
| Fixed remaining | ₹2,500 |
| Variable + isolated spent to date | ₹42,000 |
| Monthly savings target (unfunded) | ₹15,000 |
| Monthly investing target (unfunded) | ₹10,000 |
| Goal reservations remaining | ₹0 |
| Buffer | ₹5,000 |

```
(93,000 + 10,000) − 2,500 − 42,000 − 15,000 − 10,000 − 0 − 5,000 = ₹28,500
```

**Safe-to-Spend = ₹28,500.** With 10 days left in the month, per-day = ₹2,850.

This example must exist as an automated test.

### FR-9 — Wishlist ("Things I Want")

| ID | Priority | Requirement |
|---|---|---|
| FR-9.1 | P0 | The user can add a wishlist item with name, estimated price, priority (High/Medium/Low), optional target month, optional URL and note. |
| FR-9.2 | P0 | Each item shows a live verdict against current Safe-to-Spend: **✅ Yes** with the remaining Safe-to-Spend after purchase, or **❌ Not yet** with the shortfall amount. |
| FR-9.3 | P0 | The affordability check is per item and independent; buying one item does not silently change others until the purchase is actually recorded. |
| FR-9.4 | P0 | For unaffordable items, the system computes **months-to-afford** = `ceil(shortfall ÷ projected_monthly_surplus)`, where projected monthly surplus = baseline income − median fixed − median variable spend of the last 3 months. If projected surplus ≤ 0, it shows "not on current cash flow" instead of a misleading number. |
| FR-9.5 | P1 | A "what if I buy these together?" mode: select multiple items and see the combined verdict, ordered by priority. |
| FR-9.6 | P1 | An item can be promoted to a **Goal** in one action, carrying over name, target amount and target date. |
| FR-9.7 | P1 | Marking an item as purchased links it to the matching transaction and archives it. |
| FR-9.8 | P2 | Price-drop reminders / target-price tracking. |

### FR-10 — Goals

| ID | Priority | Requirement |
|---|---|---|
| FR-10.1 | P0 | A goal has: name, target amount, current amount, optional target date, priority, optional linked account. |
| FR-10.2 | P0 | Each goal shows progress as amount and percentage, with a progress bar. |
| FR-10.3 | P0 | The user can record a contribution to a goal manually. |
| FR-10.4 | P1 | Contributions can be auto-detected from transfers into a linked account. |
| FR-10.5 | P1 | For goals with a target date, the system shows required monthly contribution and whether the user is on track, behind, or ahead. |
| FR-10.6 | P1 | An **Emergency Fund** goal is created by default at 6× median monthly essential expenses (fixed + median variable), recalculated as data accumulates, and is prioritised above discretionary goals in advice. |
| FR-10.7 | P1 | The user can reserve a monthly amount toward a goal; reservations reduce Safe-to-Spend per FR-8.3. |

### FR-11 — Financial rules and advice

The differentiating requirement. The app must produce statements about the user's situation, not just totals.

| ID | Priority | Requirement |
|---|---|---|
| FR-11.1 | P0 | The system computes and displays a monthly financial summary in plain language, e.g.: *"Your baseline income is ₹93,000. Your recurring commitments are ₹18,000. Your median discretionary spend over the last 3 months is ₹24,000. You can comfortably allocate about ₹25,000/month to savings and investing."* |
| FR-11.2 | P0 | Every figure in that statement is derived from the user's actual transaction history, never from a hardcoded assumption or an LLM guess. The LLM may phrase; it may not compute. |
| FR-11.3 | P0 | The recommended monthly allocation = `baseline_income − median_fixed − median_variable_spend − buffer`, floored at 0, rounded down to the nearest ₹500. |
| FR-11.4 | P0 | Advice requires a minimum of 2 complete months of data. Below that, the app states plainly that it does not yet have enough history and shows what it has. |
| FR-11.5 | P1 | Rules are user-editable: savings rate, investing rate, buffer size, variable-income split, isolated-category list, low-confidence threshold. |
| FR-11.6 | P1 | Anomaly notices: a category exceeding its 3-month median by >50%, a new recurring charge appearing, a fixed commitment increasing in price, an unusually large single transaction. |
| FR-11.7 | P1 | Advice must be framed as information and trade-offs, not instruction. It never uses guilt, streaks, or gamified pressure. |
| FR-11.8 | P0 | Every screen presenting financial guidance carries a persistent disclaimer that this is an informational tool, not regulated financial advice. |

### FR-12 — Variable income allocation

| ID | Priority | Requirement |
|---|---|---|
| FR-12.1 | P0 | When variable income is received, the app proposes a split using the configured rule (default 50% invest / 30% goals & emergency fund / 20% discretionary). |
| FR-12.2 | P0 | Only the discretionary slice enters Safe-to-Spend. The remainder is treated as committed until the user actively overrides it. |
| FR-12.3 | P0 | The user can override any proposed split for that specific inflow, with the original recommendation kept visible. |
| FR-12.4 | P1 | The app tracks whether proposed allocations were actually executed (money moved) and shows the gap between plan and reality. |
| FR-12.5 | P1 | The app shows the counterfactual: *"₹50,000 this month → invested, this is worth ~₹X in 10 years at 10%."* Any projection must state its assumed rate and that returns are not guaranteed. |

### FR-13 — Accounts and net worth

| ID | Priority | Requirement |
|---|---|---|
| FR-13.1 | P0 | The user can register accounts: bank, cash, credit card, brokerage, mutual fund folio, PPF/EPF, other asset, other liability. |
| FR-13.2 | P0 | Each account has a current balance, updated by import (closing balance) or manually. |
| FR-13.3 | P1 | Net worth = Σ assets − Σ liabilities, shown with a month-over-month change. |
| FR-13.4 | P1 | Net worth is snapshotted monthly so a trend line can be drawn. |
| FR-13.5 | P1 | Credit card accounts are handled correctly: spending on the card is an expense at transaction time; the bill payment from the bank is a transfer, not a second expense. |

### FR-14 — Investments

| ID | Priority | Requirement |
|---|---|---|
| FR-14.1 | P1 | The user can record holdings: instrument name, type (index fund / active fund / debt / stock / gold / FD / EPF), invested amount, current value, last updated. |
| FR-14.2 | P1 | The portfolio view shows allocation by type, total invested, current value, and absolute gain/loss. Values are user-updated; no live price feed in v1. |
| FR-14.3 | P1 | The app presents a **sequence**, not a recommendation set: emergency fund first → then diversified long-term investing → then optional individual stocks. It shows which stage the user is currently in based on their data. |
| FR-14.4 | P1 | Educational content references general principles (diversification, long-term horizon, SIP as a periodic investment method rather than market timing) and is clearly attributed as general information, consistent with SEBI/AMFI investor-education material. |
| FR-14.5 | P0 | The app must never name a specific fund, stock, or product as a recommendation to buy. |
| FR-14.6 | P2 | Optional NAV lookup for mutual funds via a public AMFI NAV file to refresh current values. |

### FR-15 — Review queue

| ID | Priority | Requirement |
|---|---|---|
| FR-15.1 | P0 | A dedicated screen lists all transactions needing attention: low confidence, uncategorised, unmatched large credits, suspected duplicates. |
| FR-15.2 | P0 | The queue supports keyboard-driven rapid triage: assign category, accept suggestion, create rule, skip. |
| FR-15.3 | P0 | Bulk actions: select multiple transactions with the same merchant and categorise them together. |
| FR-15.4 | P1 | The queue shows the LLM's suggested category and its confidence as a one-click accept. |

### FR-16 — Reporting and data portability

| ID | Priority | Requirement |
|---|---|---|
| FR-16.1 | P1 | Month-over-month comparison: spending by category across the last 6 or 12 months. |
| FR-16.2 | P1 | Export all transactions to CSV, filtered by date range and category. |
| FR-16.3 | P1 | Full data export as JSON (transactions, rules, goals, wishlist, accounts, settings) — the user's data is theirs and must be extractable in one action. |
| FR-16.4 | P2 | Import of a previously exported JSON bundle. |

---

## 8. Non-functional requirements

| ID | Category | Requirement |
|---|---|---|
| NFR-1 | Performance | Dashboard for a month with ≤2,000 transactions renders in <1.5s on a local instance (p95). |
| NFR-2 | Performance | Parsing + categorising a 1,000-row CSV completes in <20s excluding LLM calls; a 40-page PDF in <60s. |
| NFR-3 | Performance | Safe-to-Spend recomputation for one month completes in <300ms server-side. |
| NFR-4 | Scale | Correct behaviour up to 100,000 transactions and 5 years of history per user. |
| NFR-5 | Correctness | All monetary arithmetic uses integer minor units. Floating-point currency arithmetic is prohibited anywhere in the stack, including the frontend. |
| NFR-6 | Correctness | All aggregation and derived-number logic is unit tested, including the FR-8.4 worked example. Minimum 85% line coverage on the `services/` layer. |
| NFR-7 | Security | Data is scoped by `user_id` at the repository layer; a test suite asserts cross-user isolation on every endpoint. |
| NFR-8 | Security | Secrets (Mongo URI, JWT signing key, LLM API key) come only from environment variables. No secret is ever committed, logged, or returned by an API. |
| NFR-9 | Privacy | Raw statement files are stored on local disk only, outside the web root, and are deletable by the user. Nothing is uploaded to third-party storage. |
| NFR-10 | Privacy | Only the **normalised merchant string** — never full descriptions, amounts, account numbers, balances, or user identity — is sent to the LLM. This constraint is enforced in code by a sanitiser with its own tests. |
| NFR-11 | Privacy | The user can disable the LLM fallback entirely in settings; the app remains fully functional. |
| NFR-12 | Reliability | Import is transactional per file: a failure mid-import leaves no partial transaction set. Failed jobs are retryable. |
| NFR-13 | Reliability | Re-running the same import is idempotent (FR-2.11). |
| NFR-14 | Usability | Fully responsive from 360px to 2560px. All primary flows usable on a phone browser. |
| NFR-15 | Accessibility | WCAG 2.1 AA: keyboard navigation for all flows, visible focus states, ≥4.5:1 contrast for text, colour never the sole carrier of meaning (priority and trend indicators need shape or text too). |
| NFR-16 | Localisation | Currency ₹ with Indian digit grouping (`₹1,43,000`). Dates day-first. Financial month = calendar month in v1 (configurable start day is P2). Timezone Asia/Kolkata. |
| NFR-17 | Observability | Structured JSON logs with a request ID. Every import job logs a durable summary. No PII, amounts, or account numbers in logs. |
| NFR-18 | Maintainability | Backend fully type-annotated with Pydantic v2 models at every boundary; frontend TypeScript `strict`. API types generated from the OpenAPI schema — no hand-written duplicate types. |
| NFR-19 | Portability | Whole stack runs locally with `docker compose up` plus one `.env`. MongoDB runs locally; no cloud dependency is required for any P0 feature. |
| NFR-20 | Backup | A documented one-command `mongodump` backup and restore procedure. |

## 9. Constraints and assumptions

- **C-1** — MongoDB runs locally (developer machine or self-hosted). It must be configured as a single-node replica set so multi-document transactions are available.
- **C-2** — Backend is Python/FastAPI; frontend is Next.js + TypeScript. Chosen partly as a learning objective, and is a fixed constraint.
- **C-3** — Single-currency (INR) in v1.
- **C-4** — The user is the only source of statement data; there is no bank connection to fall back on, so parser robustness is disproportionately important.
- **A-1** — Statements are from Indian banks in reasonably standard formats.
- **A-2** — The user is willing to spend a few minutes correcting categories on the first import in exchange for near-zero effort afterwards.

## 10. Acceptance criteria by milestone

**M1 — Ingest and see (P0 core)**
Register/login works and data is user-scoped. A CSV and an XLSX statement import correctly, with duplicate detection. Transactions list with filters and manual category editing. Seed rules apply. Cross-user isolation test suite passes.

**M2 — Learn**
PDF import works, including password-protected files. LLM fallback runs once per unknown merchant and caches. Correcting a category offers rule creation with backfill preview. Review queue functional. Rules management screen works.

**M3 — Decide**
Income sources configured and matched. Recurring detection with user confirmation. Dashboard with all tiles. Safe-to-Spend implemented, matching the FR-8.4 worked example exactly in an automated test, with a working explain-waterfall.

**M4 — Plan**
Wishlist with affordability verdicts and months-to-afford. Goals with progress and reservations. Emergency fund default goal. Variable-income allocation proposals.

**M5 — Advise**
Monthly plain-language financial summary from real history. Anomaly notices. Accounts and net worth. Investment holdings and the staged investing view. CSV/JSON export.

## 11. Open questions

| ID | Question | Needed by |
|---|---|---|
| Q-1 | Which banks' statement formats must be supported on day one? Real sample files are required before the parser can be considered done. | M1 |
| Q-2 | Should the financial month start on salary credit date rather than the 1st? | M3 |
| Q-3 | How should credit-card spending be surfaced — as spending in the month of purchase (recommended) or the month of bill payment? | M3 |
| Q-4 | Should cash withdrawals default to "unknown spending" or be excluded from variable spend until split? | M3 |
| Q-5 | Is deployment ever going beyond localhost? That decides whether HTTPS, rate limiting and CSRF hardening become P0. | M2 |

---

*This document is informational. The application it describes is a personal finance tracking tool and does not provide regulated investment, tax, or legal advice.*
