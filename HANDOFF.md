# Session handoff — Dealer Communication Portal (lead-gen-sync)

_Last updated: 2026-10-08. Start a new session by reading this file, then `README.md`, `backend/README.md`
and `BACKEND_PLAN.md`._

## 1. What this is

**DealerConnect**: an enterprise B2B portal for ABC Corporation (an electrical equipment company) to find
dealers by country / region / sector and communicate with them, plus Excel sales upload, analytics and a
12-month sales forecast.

| Part | Stack | Where |
|---|---|---|
| Frontend | Next.js 16 (App Router), React 19, **JavaScript**, MUI 9, Redux Toolkit, React Hook Form, Recharts 3 | `frontend/` (`frontend/src/`, `frontend/public/`) |
| Backend | Python 3.14 venv, FastAPI, SQLAlchemy 2 (**sync** sessions), psycopg 3, Alembic, Pydantic 2, pwdlib/Argon2, PyJWT, openpyxl | `backend/` |
| Database | PostgreSQL on **Supabase** (PG 17), schema **`dcp`** (27 tables) | `database/` (SQL), `backend/alembic/` |

## 2. Current state (all working, verified)

- Frontend is fully wired to the API (no mock data left). Login → dealers (server-side filters, facets, pagination) →
  dealer details → messages with attachments → communications → dashboard → company / profile / settings →
  Upload Sales (stored server-side, "Recent uploads" reopen / download / delete) → Sales Forecast.
- Backend: 34+ endpoints under `/api/v1`, cookie auth with refresh rotation + CSRF, tenant scoping by company.
- **Supabase database is migrated to `0002_sales_upload_detail` (head)** and seeded (57 dealers, 40 sectors /
  553 sub-sectors, company ABC Corporation, user john.smith@abc.com with a password the user chose — Claude
  does not know it).
- Tests: backend **49 passed** (14 unit + 35 integration); `npx next build` (from `frontend/`) passes.
- Git: repo initialised, remote **`https://github.com/sujaydevroy/lead-gen-sync`**, branch **`master`**,
  one pushed commit `d87a24d`. **Uncommitted:** `.gitignore` (ignore every `.env.*` except `.env.example`,
  so `backend/.env.bak` from `setup_env.py` can never be committed). Ask before committing.
- Last session left both dev servers running via the Browser pane launch configs (`portal-dev` :3000,
  `api-dev` :8000). They may not be running in a new session.

## 3. Working rules for this user (important)

- **Never `git commit` / `git push` without explicit permission in the current message** (global
  `~/.claude/CLAUDE.md`). Show `git diff --stat` and ask "Ready to commit / push — want me to?". A push may deploy.
- **The user does not see text written between tool calls.** Put answers, commands and results in the
  **final message** of the turn. (They missed the git instructions twice because of this.)
- The user is **new to Python**: give exact, copy-paste PowerShell commands, one per code block, and say
  which folder to run them in (most backend commands must run from `backend/`).
- The user's terminal is **PowerShell** on Windows. The Terminal-panel integration (`run_in_terminal`) failed
  to start a shell last time — give commands instead of relying on it.
- **Do not connect to or write test data into the user's Supabase database.** Test against a throwaway local
  cluster (see §6). Do not read or print `backend/.env` (it holds the Supabase password).
- The user's API runs with `--reload`, so backend code edits go live against Supabase immediately. If a change
  needs a migration, tell the user to run `.venv\Scripts\python -m app.cli setup` (from `backend/`) **right away**.

## 4. How to run

From the repo root, Browser-pane launch configs exist in `.claude/launch.json`:
`portal-dev` (Next.js :3000) and `api-dev` (uvicorn :8000, reads `backend/.env`).

Manually (PowerShell):

```powershell
cd D:\Projects\Personal\lead-gen-sync\backend
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```
```powershell
cd D:\Projects\Personal\lead-gen-sync\frontend
npm run dev
```

- App: http://localhost:3000 · API docs: http://localhost:8000/docs · health: http://localhost:8000/health
- Frontend → API: browser calls `/api/v1/*` on :3000, forwarded by the rewrite in `frontend/next.config.mjs` to
  `API_ORIGIN` (`frontend/.env.local`, default `http://localhost:8000`; resolved at **build** time too).
- Setup / upgrade a database (idempotent; migrations + seed + backfill + demo data + admin password):
  `.venv\Scripts\python -m app.cli setup` (from `backend/`). Create `backend/.env` with
  `.venv\Scripts\python setup_env.py` (asks for the Supabase **Session pooler** string + password).

## 5. Layout (key files)

```
frontend/src/   (frontend/package.json, next.config.mjs, public/ alongside)
  app/(portal)/...        authenticated pages: dashboard, dealers, dealers/[dealerId], communications,
                          sales (Upload Sales), forecast, company, profile, settings
  app/login, app/reset-password
  proxy.js                Next 16 "middleware": redirects signed-out users (cookie *hint* only)
  lib/apiClient.js        fetch wrapper: cookies, X-CSRF-Token, one shared refresh on 401, ApiError,
                          sign-in epoch guard, dev options (simulate errors / extra latency)
  services/*.js           thin API wrappers (auth, dealer, company, communication, sales, settings)
  store/                  Redux: salesSlice (in-page sales workspace), dealerListSlice, settingsSlice
  lib/salesAnalytics.js, lib/salesForecast.js   analytics + forecast run in the browser
  components/providers/   AuthProvider (verified flag, company + sectorDefinition), SettingsSync
backend/
  app/main.py, app/cli.py (setup, seed, set-password, seed-demo-communications, remap-products,
                           backfill-sales-uploads)
  app/core/               config (.env), database (run_sql_script), security, errors, rate limit, email (log only)
  app/models/             mirror database/02_schema.sql
  app/repositories/dealer_repository.py   dealer filters / facets SQL
  app/services/           auth, dealer, company, communication, sales, sales_upload_details,
                          exchange_rate, storage (local disk), user
  app/services/analytics/ Python ports of the JS parsing / analytics / forecast (exact parity)
  alembic/versions/       0001_baseline (runs 02_schema.sql), 0002_sales_upload_detail
  setup_env.py            interactive .env creator (URL-encodes the password)
  tests/unit, tests/integration
database/
  02_schema.sql (complete current schema), migrations/0002_sales_upload_detail.sql,
  03_seed.sql (generated by generate_seed.py from dealers.json + sector.json), generate_erd.py
data-crawler-service/   placeholder (main.py) for the future crawler service
BACKEND_PLAN.md, ERD.md, erd.html, HANDOFF.md, *.pptx   docs at the repo root
dealers.json, sector.json, sample_sales.xlsx   source data (root); frontend/public/samples/sample_sales.xlsx (demo)
```

## 6. Testing

Backend (from `backend/`): unit tests need nothing; integration tests need a disposable DB whose name
ends in `_test` (the suite drops and recreates schema `dcp`).

Throwaway cluster recipe (PostgreSQL 18 binaries at `C:\Program Files\PostgreSQL\18\bin`; the user's own
server on **5432 must not be touched** — use port **55432** and the scratchpad dir):

```bash
initdb -D <scratch>/pgtest -U postgres -A trust -E UTF8
pg_ctl -D <scratch>/pgtest -o "-p 55432" -w start
psql -h localhost -p 55432 -U postgres -c "CREATE DATABASE dealer_portal_test"
TEST_DATABASE_URL=postgresql://postgres@localhost:55432/dealer_portal_test .venv/Scripts/python -m pytest -q
pg_ctl -D <scratch>/pgtest -m fast stop   # then delete the folder
```

To run the full app against a throwaway DB without touching Supabase: start uvicorn on another port (e.g. 8010)
with `DATABASE_URL`, `JWT_SECRET`, `STORAGE_LOCAL_DIR` set as **environment variables** (they override
`backend/.env`), and point the frontend at it via `API_ORIGIN` — restore `frontend/.env.local` to :8000 afterwards.

Parity checks (frontend JS == backend Python) on `sample_sales.xlsx`, all currencies → USD:
total 5,159,935; SES α=0.4; 12-month base 1,663,490, conservative 485,974, optimistic 4,340,990, growth −6.2%.
Dealer filters: India+North+Active = 3; India|Germany + North|South + Active = 7; Electrical + Switchgear = 18.

Frontend: `npx next build` from `frontend/` (no ESLint configured; `next lint` no longer exists in Next 16).

## 7. Design decisions worth knowing

- Every table has `id, is_active, created_by, created_on, modified_by, modified_on` (requested SQL Server
  style mapped to PostgreSQL snake_case; `modified_on` trigger on every table; soft delete only).
  `created_by/modified_by` are filled from `session.info["user_id"]` (set in `api/deps.py`), not FKs.
- All tables live in schema `dcp` (not exposed by Supabase's Data API). Every query is schema-qualified
  (no `search_path` startup option — Supavisor rejects it).
- API JSON shapes match what the frontend services always returned (dealers use `dealers.json` snake_case
  keys; most other objects camelCase). "Not Available" ↔ NULL conversion happens in the API.
- Auth: `dcp_access` JWT cookie (15 min), `dcp_refresh` opaque cookie (path `/api/v1/auth`, rotation +
  reuse detection), `dcp_csrf` double-submit cookie/header; `/auth/token` gives bearer tokens for Swagger.
- Sales upload storage = master/detail: `sales_uploads` (file name, original name, sheet, sha256,
  `storage_path`, `physical_path`, counts) → `sales_upload_columns`, `sales_upload_rows` (all cells JSONB,
  valid or not, linked to `sales_records`), `sales_records` (typed rows for analytics), `sales_upload_issues`.
  Files are stored on local disk under `backend/storage/` (gitignored).
- Redux sales workspace is intentionally cleared by a full browser refresh (original requirement); uploads
  persist on the server and are reopened from "Recent uploads".
- Forecast: SES / Holt / damped Holt chosen by AICc (6–23 months), Holt-Winters at 24+, OLS at 3–5;
  95% bounds; scenarios = 16th/84th percentile of 2,000 seeded simulations (mulberry32 + Box-Muller,
  identical in JS and Python; `js_sum` avoids Python's compensated `sum()`).
- Exchange rates: global defaults + company overrides (admins only) in `dcp.exchange_rates`.

## 8. Gotchas already solved (don't re-learn)

- psycopg treats `%` in SQL scripts as placeholders → use `app.core.database.run_sql_script` (raw cursor).
- Client IP is stored in an `INET` column → validate it (`api/deps.client_ip`).
- Windows consoles (cp1252) can't print ✓ / ✗ when output is piped → CLI prints ASCII only.
- Supabase direct host `db.<ref>.supabase.co` is IPv6-only; this PC has no IPv6 → use the **Session pooler**
  host (`aws-0-ap-southeast-1.pooler.supabase.com:5432`, user `postgres.<ref>`). `@` in passwords must be `%40`.
- Next 16: `middleware.js` is now `proxy.js`; rewrites are baked in at build time.
- Stale cached session from the old mock version caused login ping-pong → login only skips the form when
  the API has *verified* the session; 401s from requests started before the latest sign-in are ignored.

## 9. Open items / ideas (nothing in progress)

1. Commit the `.gitignore` change (ask first).
2. Email delivery for password reset is log-only (`app/core/email.py`) — needs a provider (plan open question 3).
3. Storage is local disk only; Supabase Storage / S3 not implemented (plan open question 7).
4. Dockerfile written but never built/tested.
5. Open product questions in `BACKEND_PLAN.md` §12 (dealer ownership, sales data lifetime,
   message delivery, sales ↔ dealer matching, Supabase Auth vs own auth, naming, attachment storage).
6. Possible UI: show stored columns / rejected rows per upload (API ready: `GET /sales/uploads/{id}/columns`,
   `/rows?valid=false`).
7. Sample sales data is tobacco products while the company is electrical — expected demo mismatch.
