# Dealer Communication Portal — API (Python + PostgreSQL)

FastAPI + SQLAlchemy 2 + psycopg 3 + Alembic. Design: [`BACKEND_PLAN.md`](../BACKEND_PLAN.md) ·
schema: [`database/02_schema.sql`](../database/02_schema.sql) · ERD: [`ERD.md`](../ERD.md).

## Quick start (Windows, from the `backend` folder)

You don't need `psql` or to run any `.sql` file yourself. `01_create_database.sql` isn't needed on
Supabase, and the commands below run `02_schema.sql` and `03_seed.sql` for you.

```powershell
.venv\Scripts\python setup_env.py            # 1. asks for the connection string + password, tests it, writes .env
.venv\Scripts\python -m app.cli setup        # 2. creates the tables, loads the data, sets John Smith's password
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000    # 3. start the API
```

Then open http://localhost:8000/docs, click **Authorize**, sign in as `john.smith@abc.com` with the
password you chose in step 2, and try any endpoint. Press `Ctrl+C` in the terminal to stop the API.

**Supabase connection string:** in your project click **Connect** (top bar) and copy the **Session pooler**
string (`postgresql://postgres.<ref>:[YOUR-PASSWORD]@aws-0-<region>.pooler.supabase.com:5432/postgres`).
The `db.<ref>.supabase.co` address only works on networks with IPv6. `setup_env.py` URL-encodes the
password for you (an `@` in the password becomes `%40`).

Both commands are safe to run again. If `02_schema.sql` was already run with psql, `setup` detects it
and only records it as migrated.

### First-time Python setup (only if `.venv` doesn't exist yet)

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
```

### Individual commands

```bash
alembic upgrade head               # creates schema "dcp" from database/02_schema.sql
python -m app.cli seed             # reference data, sectors, company, John Smith, 57 dealers (idempotent)
python -m app.cli set-password john.smith@abc.com    # prompts; the seeded user has no password
python -m app.cli seed-demo-communications           # optional demo history
python -m app.cli backfill-sales-uploads             # fill column/row detail for uploads made before migration 0002
python -m app.cli create-sysadmin you@example.com --name "Your Name"   # System Administrator (prompts for the password)
```

**Updating an existing database:** after pulling new code, run `.venv\Scripts\python -m app.cli setup` again. It applies
new migrations (e.g. 0002 = sales upload columns/rows tables) and completes older uploads; everything else is unchanged.

- Interactive docs: http://localhost:8000/docs (use **Authorize** with your email + password)
- Health check: http://localhost:8000/health

## Tests

```bash
pytest                                                           # unit tests only
set TEST_DATABASE_URL=postgresql://postgres@localhost:5432/dealer_portal_test
pytest                                                           # + integration tests
```

Integration tests **drop and recreate** schema `dcp` in `TEST_DATABASE_URL`. The database name must end in
`_test` or the run is refused.

## What's implemented

| Area | Endpoints (prefix `/api/v1`) |
|---|---|
| Auth | `POST /auth/login` (cookies), `/auth/token` (bearer), `/auth/refresh`, `GET /auth/session`, `POST /auth/logout`, `/auth/forgot-password`, `/auth/reset-password` |
| Users | `GET/PATCH /users/me`, `POST /users/me/password`, `GET/PUT /users/me/settings`; Company Administrators: `GET/POST /users`, `GET /users/roles`, `PATCH /users/{id}` (role, isActive), `POST /users/{id}/unlock`, `POST /users/{id}/password` |
| System administration | System Administrators only: `GET /admin/lookups`, `GET/POST /admin/companies`, `GET/PUT/DELETE /admin/companies/{id}`, `POST /admin/companies/{id}/activate`, `GET /admin/companies/{id}/users`, `PATCH /admin/companies/{id}/users/{userId}` (+ `/unlock`, `/password`), `GET /admin/dealer-directory`, `POST /admin/dealer-uploads` (.xlsx / .xls / .csv / .json into the dealer directory — `dcp.dealers`, owned by no company — + product tables), `GET /admin/dealer-uploads/template` |
| Dealers | `GET /dealers` (search, 6 filter groups, facets, pagination), `/dealers/search`, `/dealers/recent`, `/dealers/{id}` |
| Communication | `POST /dealers/{id}/messages` (multipart + attachment), `POST /dealers/{id}/interactions`, `GET /communications`, `/communications/recent`, `/communications/stats`, attachment download |
| Company & lookups | `GET /companies/me`, `PUT /companies/me` (Company Administrators), `/companies/me/options`, `/companies/me/sector`, `/lookups/*`, `/dashboard/stats` |
| Sales | `POST /sales/uploads`, `/sales/uploads/sample`, `GET/DELETE /sales/uploads/{id}`, `GET /sales/uploads`, `GET /sales/uploads/{id}/columns`, `/sales/uploads/{id}/rows`, `/sales/uploads/{id}/file` (original workbook), `GET/PUT/DELETE /sales/exchange-rates`, `GET /sales/analytics`, `GET /sales/forecast` |

Security: Argon2id password hashes, 15-minute JWT access cookie, rotating refresh sessions with reuse
detection, double-submit CSRF header for cookie-authenticated writes, login lockout and rate limiting,
tenant scoping by company on every query, role checks for exchange-rate changes, user management and system administration, upload type/size checks,
and no SQL string building with user input.

The Next.js frontend calls this API through its `/api/v1` rewrite (see the root README). No email provider is
configured, so password-reset emails are written to the log (`app/core/email.py`). Files are stored on
local disk (`STORAGE_LOCAL_DIR`).

## Layout

```
app/
  main.py              app factory, middleware, /health
  cli.py               set-password, seed, seed-demo-communications, remap-products, create-sysadmin
  core/                config, database, security, errors, rate limiting, email
  models/              SQLAlchemy models (mirror database/02_schema.sql)
  schemas/             Pydantic request/response models (same JSON keys the frontend uses)
  repositories/        dealer list SQL (filters, facets, pagination)
  services/            business logic; services/analytics = Python ports of the frontend's
                       salesParsing / salesAnalytics / salesForecast / sectorMatching
  api/v1/              routers
alembic/               migrations (0001 = baseline from database/02_schema.sql)
tests/                 unit (parity with the JavaScript results) + integration (real PostgreSQL)
```
