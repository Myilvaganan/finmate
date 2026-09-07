# FinMate — Your Money. Smarter.

A personal finance intelligence platform: upload bank statements in almost any format, get
normalized transactions, automatic categorization, deterministic financial analytics, and an
AI assistant that answers questions grounded in your real data.

Branding lives in one place — [`frontend/src/config/brand.ts`](frontend/src/config/brand.ts) —
so the product name/tagline can change without touching the rest of the app.

## Architecture

```
React (Vite/TS/Tailwind) ──HTTP──▶ FastAPI ──▶ Services / Analytics Engine ──▶ SQLAlchemy ──▶ SQLite
                                       │
                                       └──▶ AI Provider abstraction (mock/openai/anthropic/gemini/local)
```

- **Frontend never talks to an AI provider directly.** All AI calls go through the backend;
  API keys live only in backend environment variables.
- **Financial numbers always come from deterministic SQL aggregation** (`app/analytics/engine.py`),
  never from an LLM. The AI layer only explains numbers the analytics engine already computed.
- **SQLite today, PostgreSQL later**: all data access goes through SQLAlchemy models — swapping
  `DATABASE_URL` to a Postgres DSN requires no business-logic changes.

### Backend layout (`backend/app/`)
- `models/` — SQLAlchemy models (users, accounts, statements, transactions, categories, merchants,
  merchant rules, recurring transactions, insights, chat, upload jobs, audit logs)
- `parsers/` — `BaseStatementParser` + CSV/Excel/TXT/HTML/PDF/OCR/Generic implementations behind a
  `ParserRegistry` that auto-detects format and bank (structurally, via column signatures — not by
  trusting a bank-name string)
- `services/` — normalization, merchant normalization, categorization, duplicate detection (exact +
  fuzzy), statement period overlap detection, balance validation, transfer/card-payment/cash
  detection, and the `StatementImportService` orchestrator (stage → review → confirm → commit)
- `analytics/` — deterministic `AnalyticsEngine`, recurring-transaction detection, smart-insight rules
- `ai/` — `AIProvider` interface + Mock/OpenAI/Anthropic/Gemini/Local implementations, a
  structured `FinancialTools` layer, and `chat_service.py` (intent → query plan → SQL → LLM explanation)
- `api/routers/` — REST endpoints, all behind `get_current_user` (JWT), all queries scoped to the
  authenticated user's own data
- `workers/job_runner.py` — background statement processing via FastAPI `BackgroundTasks`
  (swappable for Celery/RQ/SQS later without changing the pipeline itself)

### Frontend layout (`frontend/src/`)
`pages/`, `layouts/`, `components/ui/`, `services/` (one file per API domain — nothing calls
`axios`/`fetch` directly from a component), `context/` (auth + theme), all wired through
TanStack Query.

## Getting started

### Backend
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env          # edit AI_PROVIDER / AI_API_KEY as needed
mkdir -p data uploads reports
alembic upgrade head              # or: rely on dev auto-create at startup
python -m app.seed                # creates demo@finmate.app / demopassword123 with 6 months of data
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev                       # http://localhost:5173, proxies /api to :8000
```

### Tests
```bash
cd backend && source .venv/bin/activate && python -m pytest -q
```
36 tests cover: the four critical statement-overlap cases (exact duplicate, partial overlap, full
containment, no overlap), fuzzy/exact transaction duplicate detection, debit/credit normalization
across bank formats, date parsing/ambiguity, rule-based categorization, merchant normalization,
transfer/card-payment/cash-withdrawal classification, balance validation, and cross-user API
authorization (one user cannot read/delete another user's accounts, statements, or transactions).

### End-to-end smoke script
A manual Playwright-driven script exercises the real browser flow (login → dashboard with live
data → theme toggle → transactions → AI assistant → statement upload → review → confirm → commit):
```bash
cd frontend && npm i -D playwright && npx playwright install chromium
node e2e/smoke.mjs   # backend on :8000 and `npm run dev` on :5173 must already be running
```

### Production build
```bash
cd frontend && npm run build      # tsc -b && vite build — verified clean
```

## Database configuration

Default is local SQLite (`DATABASE_URL=sqlite:///./data/finmate.db`). Two ways to point at Postgres:

**Plain connection string** (any Postgres, including RDS with a static password):
```env
DATABASE_URL=postgresql+psycopg2://<user>:<password>@<host>:5432/<db_name>
```

**AWS RDS IAM authentication** (no stored DB password — a short-lived token is generated per
connection via `boto3`, using whatever AWS credentials are ambient to the process: env vars,
`~/.aws/credentials`, or an EC2/ECS instance role):
```env
RDS_IAM_AUTH=true
RDS_HOST=<your-instance>.<id>.<region>.rds.amazonaws.com
RDS_PORT=5432
RDS_DB_NAME=finmate
RDS_USER=<db_username>
AWS_REGION=<region>
```
The DB user needs `rds_iam` granted (`GRANT rds_iam TO <db_username>;`) and the IAM principal
needs an `rds-db:connect` policy for that instance/user. Verify connectivity any time with:
```bash
python scripts/check_db_connection.py
```

## AI configuration

```env
AI_PROVIDER=mock      # none | mock | openai | anthropic | gemini | local
AI_API_KEY=
AI_MODEL=
AI_BASE_URL=          # only used by the local provider (Ollama/LM Studio/vLLM, OpenAI-compatible)
```

- `none` — AI features degrade gracefully; the app (parsing, normalization, duplicate/overlap
  detection, analytics, dashboard, transaction management) works fully without it.
- `mock` — deterministic canned responses so the whole app (including chat and categorization
  fallback) is developable/demoable with zero API keys. **This is the default.**
- `openai` / `anthropic` / `gemini` / `local` — set `AI_API_KEY` (and `AI_MODEL`/`AI_BASE_URL` as
  needed) in the backend `.env`. Never put a key in the frontend or commit `.env`.

## Security notes
- Passwords hashed with bcrypt; JWT bearer tokens for auth.
- Every account/statement/transaction/chat-session query is filtered by the authenticated user's
  id server-side — IDs from the client are never trusted as ownership proof (see `tests/test_api_authorization.py`).
- Uploaded files are validated by magic bytes (not just extension), size-capped, written to a
  UUID-named path under `uploads/`, and deleted after processing. Raw statement contents are never logged.
- Standardized error envelope (`{success, error: {code, message, details}}`) with typed error codes
  (`INVALID_FILE`, `DUPLICATE_STATEMENT`, `BALANCE_MISMATCH`, `AI_UNAVAILABLE`, …).

## Known scope limits (honest accounting)

This was built as a working, end-to-end vertical slice rather than an exhaustive implementation of
every line item in a 100+ requirement spec. Verified and real (not mocked):

- Full ingestion pipeline: parse → normalize → validate → overlap/duplicate detect → categorize →
  stage → **mandatory review screen** → confirm → commit, for CSV/XLSX/TXT/HTML/PDF (table-based),
  with an OCR path that degrades clearly if `tesseract` isn't installed on the host.
- Deterministic analytics engine, dashboard, transactions table (server-paginated), AI chat grounded
  in real SQL queries, Alembic migrations, demo seed data, 36 passing tests, clean prod build.

Deliberately lighter than the full spec, in the interest of shipping a coherent working system:
- **Design system**: hand-built Tailwind components in the spec's visual direction, not the full
  shadcn/ui CLI component set.
- **Categorization AI fallback**: wired through the provider abstraction and used per-transaction
  when rules don't match, but not micro-tuned/batched for large statements.
- **Reports/export**: JSON/CSV/XLSX generation works; PDF export and a full reports gallery UI are
  not built out.
- **Credit-card statement double-counting, investment tracking, financial health score, subscription
  management UI, email-ingestion interface**: modeled in the data layer or partially covered by
  transfer/category detection, but don't have dedicated UI/flows yet.
- **Accessibility and mobile**: responsive layout and a mobile bottom nav exist; a full ARIA/focus-trap
  audit hasn't been done.

None of the above are faked in the running app — they're just not built yet. Everything that *is*
present is real: no hard-coded dashboard numbers, no stub endpoints, no fake charts.
