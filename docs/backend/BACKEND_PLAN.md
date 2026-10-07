# Backend Plan — Dealer Communication Portal (Python + PostgreSQL)

**Status:** backend phases 0–5 implemented in [`backend/`](../../backend/README.md) (44 tests passing);
frontend connected to the API (§8 done, verified end to end) · **Scope:** replace the frontend's mock data and mock auth
with a real API backed by PostgreSQL (Supabase-hosted or self-hosted).

> **Implementation notes (differences from the original plan)**
> - **Sync SQLAlchemy sessions** (FastAPI runs the endpoints in its thread pool) instead of async:
>   psycopg's async mode doesn't work with Windows' default event loop, and sync code is simpler at
>   this scale. Moving to async later only affects `app/core/database.py` and the repositories.
> - The forecast port is **pure Python** (no numpy / statsmodels needed). It reproduces the
>   frontend's results exactly on `sample_sales.xlsx`.
> - Repository modules exist for the dealer list (the complex SQL); communication and sales queries
>   live in their services.
> - Extra endpoint `POST /auth/token` (OAuth2 password flow → bearer token) for API clients and the Swagger UI.
> - Only local-disk file storage and log-only email are implemented (open questions 3 and 7).

Related deliverables:

| File | What it is |
|---|---|
| [`database/01_create_database.sql`](../../database/01_create_database.sql) | Optional `CREATE DATABASE` for self-hosted PostgreSQL (skip on Supabase) |
| [`database/02_schema.sql`](../../database/02_schema.sql) | Full schema: 27 tables, constraints, indexes, `modified_on` triggers |
| [`database/migrations/`](../../database/migrations/) | Upgrades for existing databases (0002: sales upload master/detail), run by Alembic |
| [`database/03_seed.sql`](../../database/03_seed.sql) | Reference data + company, user and the 57 dealers (generated) |
| [`database/generate_seed.py`](../../database/generate_seed.py) | Regenerates the seed from `sector.json` and `dealers.json` |
| [`database/generate_erd.py`](../../database/generate_erd.py) | Regenerates the ERD from the live schema |
| [`ERD.md`](ERD.md) / [`erd.html`](erd.html) | Entity-relationship diagrams (Mermaid) |

---

## 1. What the frontend needs today

The Next.js app already isolates data access in `src/services/*`. Every UI component calls these
methods, which currently return mock data with simulated latency. The backend must provide the same
operations with the same response shapes, so the switch only touches the service files.

| Frontend service method | Current mock source | Backend responsibility |
|---|---|---|
| `authService.login / logout / getSession` | `src/app/api/auth/*` (HMAC cookie, password from `.env.local`) | Real users, Argon2 password hashes, JWT + refresh sessions |
| `authService.requestPasswordReset` | timeout only | Reset tokens + email delivery |
| `authService.updateProfile` | `localStorage` | `PATCH /users/me` |
| `dealerService.getDealers` (search, 6 filter groups, facets, pagination) | `dealers.json` + `lib/dealerFiltering.js` | SQL filtering, facet counts, server-side pagination |
| `dealerService.getDealerById / searchDealers / getRecentDealers / getDealerStats` | `dealers.json` | Dealer reads scoped to the user's company |
| `dealerService.getCountries / getRegions` | derived from dealers | Lookup endpoints with counts |
| `companyService.getCompanyDetails / getCompanySectorDefinition` | `src/data/companies.js` + `sector.json` | Company + sector / sub-sectors |
| `communicationService.getCommunicationHistory / getRecentCommunications / getCommunicationStats` | in-memory array | `communications` table |
| `communicationService.sendMessage` (with attachment) | in-memory push | Persist message + attachment file |
| `communicationService.logInteraction` (Email / Call buttons) | in-memory push | Persist interaction |
| `salesService.parseSalesFile / loadSampleFile` | browser Excel parsing (`read-excel-file`) | Server-side upload, validation, persistence |
| Sales analytics + 12-month forecast | `lib/salesAnalytics.js`, `lib/salesForecast.js` | Phase 2: same calculations server-side |
| Settings (page size, instant filters, layout) | `localStorage` | `user_settings` table |
| Exchange rates (editable on Upload Sales) | Redux (`lib/fx.js` defaults) | `exchange_rates` (global + company overrides) |

## 2. Technology choices

| Concern | Choice | Why |
|---|---|---|
| Language | Python 3.12 or 3.13 | Mature library support (3.14 works locally but some wheels lag) |
| Web framework | **FastAPI** + Uvicorn | Pydantic validation, OpenAPI docs for the frontend team |
| ORM / SQL | **SQLAlchemy 2.0** (sync sessions) + **psycopg 3** | Typed models, composable queries for the dynamic filters |
| Migrations | **Alembic** | Baseline = `database/02_schema.sql`; later changes as revisions |
| Validation / DTOs | Pydantic v2 (+ `pydantic-settings` for config) | Response models can emit the exact keys the UI expects |
| Passwords | `pwdlib[argon2]` (Argon2id) | Current best practice |
| Tokens | PyJWT (access) + opaque refresh tokens (hashed in DB) | Revocable sessions, "Remember me" support |
| Excel | `openpyxl` (read-only mode) | Same rules as `lib/salesParsing.js` |
| Forecasting | Pure-Python port of `lib/salesForecast.js` | Keep results identical to the current UI |
| File storage | `StorageService` interface → Supabase Storage / S3 / local disk | Attachments and uploaded workbooks |
| Tests | pytest, httpx `AsyncClient`, a disposable PostgreSQL | Unit + API + parity tests |
| Quality | ruff (lint + format), mypy (optional) | |

## 3. Architecture

```
Next.js UI ──► src/services/*.js ──► Next.js rewrite /api/v1/* ──► FastAPI
                                                                    │
                    routers (HTTP, auth, validation) ◄──────────────┘
                              │
                    services (business rules, tenant scoping, facets, forecasting)
                              │
                    repositories (SQLAlchemy queries)
                              │
                    PostgreSQL schema "dcp"      StorageService (files)
```

- **Same-origin calls:** add a Next.js rewrite from `/api/v1/:path*` to the FastAPI host. Cookies
  stay first-party and httpOnly, and no CORS setup is needed in production.
- **Tenant isolation:** `company_id` always comes from the authenticated user, never from request
  parameters. Every repository query for business data filters by it.
- **Thin routers, testable services:** routers only translate HTTP ⇄ service calls.

### Project layout

```
backend/
├── pyproject.toml
├── .env.example
├── alembic.ini
├── alembic/
│   └── versions/0001_baseline.py        # executes database/02_schema.sql
├── app/
│   ├── main.py                          # FastAPI app, routers, middleware, /health
│   ├── cli.py                           # set-password, import-dealers, import-sectors
│   ├── core/
│   │   ├── config.py                    # Settings (env vars)
│   │   ├── database.py                  # async engine + session dependency
│   │   ├── security.py                  # hashing, JWT, cookies, CSRF
│   │   └── errors.py                    # error model {"message": ...} like the mock API
│   ├── models/                          # SQLAlchemy models (AuditMixin on every table)
│   │   ├── base.py  lookups.py  company.py  user.py  dealer.py  communication.py  sales.py
│   ├── schemas/                         # Pydantic request/response models
│   ├── repositories/                    # query code (dealer_repository.py, ...)
│   ├── services/
│   │   ├── auth_service.py  dealer_service.py  company_service.py
│   │   ├── communication_service.py  sales_service.py  storage_service.py
│   │   └── analytics/  sales_analytics.py  sales_forecast.py  sector_matching.py
│   └── api/
│       ├── deps.py                      # get_db, get_current_user, require_role
│       └── v1/  auth.py  users.py  dealers.py  lookups.py  companies.py
│                communications.py  sales.py  dashboard.py
└── tests/
    ├── unit/  integration/  parity/
    └── conftest.py
```

### Common columns (requested) → PostgreSQL

| Requested (SQL Server style) | Implemented as | Notes |
|---|---|---|
| `Id bigint primary key` | `id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY` | Identity column (PostgreSQL has no `IDENTITY(1,1)` keyword form) |
| `IsActive bit default 1 not null` | `is_active BOOLEAN NOT NULL DEFAULT TRUE` | PostgreSQL `boolean` is the idiomatic `bit` |
| `CreatedBy BigInt` | `created_by BIGINT` | Set by the API from the current user; NULL for system/imports |
| `CreatedOn datetime default getdate() not null` | `created_on TIMESTAMPTZ NOT NULL DEFAULT now()` | `getdate()` → `now()`; time zone–aware |
| `ModifiedBy BigInt` | `modified_by BIGINT` | Set by the API on update |
| `ModifiedOn datetime default getdate() not null` | `modified_on TIMESTAMPTZ NOT NULL DEFAULT now()` | Plus a `BEFORE UPDATE` trigger on every table |

Names use `snake_case` because PostgreSQL folds unquoted `PascalCase` to lower case (`IsActive` →
`isactive`). If PascalCase is mandatory, every identifier must be double-quoted everywhere. That's
possible but not recommended.

`created_by` / `modified_by` are intentionally **not** foreign keys. That avoids a circular
dependency with `users`, and import jobs can write rows without a user. Soft delete =
`is_active = FALSE`; the API never hard-deletes business rows.

SQLAlchemy mixin used by every model:

```python
class AuditMixin:
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)
    created_by: Mapped[int | None] = mapped_column(BigInteger)
    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    modified_by: Mapped[int | None] = mapped_column(BigInteger)
    modified_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),
                                                  onupdate=func.now(), nullable=False)
```

A session `before_flush` hook fills `created_by` / `modified_by` from the request's user id
(held in a `contextvars.ContextVar` set by the auth dependency).

## 4. Database design (summary)

Full DDL: [`database/02_schema.sql`](../../database/02_schema.sql) · Diagram: [`ERD.md`](ERD.md).
All objects live in schema **`dcp`**. On Supabase this keeps them out of the auto-generated Data
API, which only exposes `public` by default.

| Area | Tables | Notes |
|---|---|---|
| Reference | `roles`, `countries`, `regions`, `currencies`, `dealer_types`, `dealer_statuses`, `communication_types`, `communication_statuses`, `sectors`, `sub_sectors` | Lookups replace the string constants in `src/types/*.js` |
| Company & auth | `companies`, `users`, `user_settings`, `user_sessions`, `password_reset_tokens` | `companies.sector_id` drives the Sector / Sub-sector filters |
| Dealers | `dealers`, `products`, `dealer_products`, `product_sub_sectors` | `product_sub_sectors` stores the product → sub-sector mapping that `lib/sectorMatching.js` computes with keywords today |
| Communication | `communications`, `communication_attachments` | One table for Email / Message / Call / Meeting, inbound and outbound |
| Sales | `sales_uploads` (master), `sales_upload_columns`, `sales_upload_rows`, `sales_upload_issues`, `sales_records`, `exchange_rates` | Master holds the file names, physical storage path and checksum. Detail stores every sheet column and every row with all cells (JSONB), plus typed `sales_records` for analytics. Raw text is kept next to resolved FKs (`customer_name` + `dealer_id`, `product_name` + `product_id`) |

Key decisions:

- **Dealers belong to a company** (`dealers.company_id`, unique `(company_id, dealer_code)`).
  `dealer_code` is the public id (`DLR-1001`) used in URLs. See open question 1.
- **"Not Available" becomes `NULL`** in the database. The API converts `NULL` back to the
  string `"Not Available"` for fields where the UI expects it, until the UI handles nulls itself.
- **Sub-sector filtering** joins `dealer_products → product_sub_sectors` instead of running regex
  at query time. When products are created or renamed, `sector_matching.py` (a port of
  `lib/sectorMatching.js`) recomputes the mapping.
- **Exchange rates:** `company_id IS NULL` rows are global defaults; company rows override them.
  Partial unique indexes enforce one rate per currency per date per scope.
- **Indexes** cover the filter columns (`company_id` + country/region/status/type/sector), dealer
  name sorting, communication timelines and sales periods. Add `pg_trgm` GIN indexes for
  substring search once the dealer volume needs them.

## 5. Authentication & authorisation

| Item | Design |
|---|---|
| Login | `POST /api/v1/auth/login` `{email, password, remember}` → verifies the Argon2id hash. Responds `{user, expiresAt}` (same as the mock) and sets cookies |
| Access token | JWT (HS256 or RS256), 15 minutes, httpOnly `Secure` `SameSite=Lax` cookie `dcp_access` |
| Refresh token | Random 256-bit value in httpOnly cookie `dcp_refresh` (path `/api/v1/auth`); only its SHA-256 hash is stored in `user_sessions`. Rotated on each refresh |
| Remember me | Refresh session 30 days with persistent cookie; otherwise 12 hours and a browser-session cookie (same behaviour as today) |
| Session check | `GET /api/v1/auth/session` → `{user, expiresAt}` or `{user: null}` (the UI already handles this) |
| Logout | Revokes the session row and clears both cookies |
| Lockout | `failed_login_count` / `locked_until` (e.g. 5 failures → 15 minutes); generic "Invalid email or password" message |
| Password reset | `POST /auth/forgot-password` always returns 202; token hash stored in `password_reset_tokens` (1-hour expiry, single use); `POST /auth/reset-password` |
| CSRF | `SameSite=Lax` cookies + a double-submit `X-CSRF-Token` header on state-changing requests |
| Roles | `roles` table; dependency `require_role("Company Administrator")` for company settings, exchange rates and user management |
| Next.js `proxy.js` | Keeps the redirect for logged-out users, keyed on the presence of the access/refresh cookie. The API remains the authority (401 → redirect to `/login`) |

Initial admin: the seed creates John Smith with `password_hash = NULL`. Set the password with
`python -m app.cli set-password john.smith@abc.com` (prompts, never on the command line).

## 6. API (v1)

All endpoints are under `/api/v1`, need authentication (except login / forgot / reset), and are
scoped to the user's company. Errors use `{"message": "..."}` (what the frontend services read).
Validation errors return 422 with field details.

### Auth & user

| Method | Path | Replaces |
|---|---|---|
| POST | `/auth/login` | `authService.login` |
| POST | `/auth/logout` | `authService.logout` |
| GET | `/auth/session` | `authService.getSession` |
| POST | `/auth/refresh` | new (silent token refresh) |
| POST | `/auth/forgot-password` · `/auth/reset-password` | `authService.requestPasswordReset` |
| GET · PATCH | `/users/me` | `authService.updateProfile` (name, job title, phone) |
| GET · PUT | `/users/me/settings` | Settings page (page size, instant filters, desktop view) |

### Dealers & lookups

| Method | Path | Replaces / notes |
|---|---|---|
| GET | `/dealers?search=&countries=&regions=&statuses=&types=&sectors=&subSectors=&page=&pageSize=` | `dealerService.getDealers`. Repeated params for multi-select. Response `{items, total, page, pageSize, totalPages, facets, totalDealers}` |
| GET | `/dealers/{dealerCode}` | `getDealerById` (404 `{message}` when missing) |
| GET | `/dealers/search?q=&limit=` | `searchDealers` (Communications → New message) |
| GET | `/dealers/recent?limit=` | `getRecentDealers` |
| GET | `/lookups/countries` · `/lookups/regions?country=` | `getCountries` / `getRegions` |
| GET | `/lookups/dealer-types` · `/lookups/dealer-statuses` · `/lookups/communication-types` | replace constants |
| GET | `/dashboard/stats` | `getDealerStats` + `getCommunicationStats` |

**Dealer list algorithm** (port of `lib/dealerFiltering.js`, must keep the same semantics):

1. Base query: `dealers WHERE company_id = :company AND is_active`.
2. Search: `ILIKE '%term%'` on `dealer_name`, `dealer_code`, `legal_name`, `city`, `contact_person`, `email`.
3. Filters: AND across groups, OR (`= ANY(:list)`) within a group. Sub-sector:
   `EXISTS (dealer_products ⨝ product_sub_sectors WHERE sub_sector_id = ANY(:ids))`.
4. Facets: one grouped count per facet, applying **every other** filter group plus the search
   (the "skip own group" rule). Regions are restricted to the selected countries; `regionsByCountry`
   is returned too.
5. `ORDER BY dealer_name`, `LIMIT :pageSize OFFSET (:page-1)*:pageSize`, `pageSize ∈ {10, 20, 50}`.

**Response field mapping.** The UI reads dealers with `dealers.json` keys; Pydantic aliases keep them:

| API field (UI) | Column |
|---|---|
| `dealer_id` | `dealer_code` |
| `company_name` | `legal_name` |
| `dealer_type`, `status`, `country`, `region`, `sector` | names from the lookup joins |
| `product` (array) | `dealer_products → products.name` ordered by `sort_order` |
| `last_transaction_amount`, `currency` | `last_transaction_amount`, `currencies.code` (string / "Not Available") |
| `created_at` | `created_on` |
| everything else | same name |

### Company

| Method | Path | Replaces |
|---|---|---|
| GET | `/companies/me` | `companyService.getCompanyDetails` (same keys as `src/data/companies.js`, `address` nested) |
| GET | `/companies/me/sector` | `getCompanySectorDefinition` → `{sector, sub_sectors: [...]}` |

### Communication

| Method | Path | Replaces / notes |
|---|---|---|
| GET | `/communications?dealerId=&types=&direction=&search=&page=&pageSize=` | `getCommunicationHistory` (keys: `id, dealerId, type, direction, sender, recipient, subject, body, status, createdAt, attachments`) |
| GET | `/communications/recent?limit=` | `getRecentCommunications` |
| GET | `/communications/stats` | `getCommunicationStats` → `{sent, received, total}` |
| POST | `/dealers/{dealerCode}/messages` (multipart: `subject`, `message`, `attachment?`) | `sendMessage`. Same validation as the form: subject 3–150, message 10–5000, file ≤ 10 MB with allowed extensions |
| POST | `/dealers/{dealerCode}/interactions` `{type: "Email"\|"Call", subject}` | `logInteraction` |
| GET | `/communications/{id}/attachments/{attachmentId}` | download (signed URL or streamed) |

The UI's auto-refresh (`communicationService.subscribe`) becomes a refetch after a successful POST.
Server-sent events can come later if live updates are needed.

### Sales

| Method | Path | Replaces / notes |
|---|---|---|
| POST | `/sales/uploads` (multipart `file`) | `parseSalesFile`. Returns `{uploadedData:{headers, rows}, processedData, fileMetadata}`, the exact shape the Redux slice stores |
| POST | `/sales/uploads/sample` | `loadSampleFile` (server reads its bundled demo workbook) |
| GET | `/sales/uploads` | list previous uploads (new) |
| GET | `/sales/uploads/{id}` | reopen an upload (same shape as POST) |
| DELETE | `/sales/uploads/{id}` | "Clear data" (soft delete) |
| GET · PUT | `/sales/exchange-rates` | FX dialog (PUT = company override, admin only) |
| GET | `/sales/analytics?uploadId=&currency=&reportingCurrency=&dateFrom=&dateTo=&customers=&products=&countries=` | Phase 2: server-side `useSalesAnalytics` result |
| GET | `/sales/forecast?…same filters…&scenario=` | Phase 2: forecast points, bounds, scenario totals, method, parameters |

**Upload processing** (port of `lib/salesParsing.js` + `services/salesService.js`):
- Accept `.xlsx` only, max 10 MB. Check the extension, the ZIP signature and the content type, and read with `openpyxl` in read-only mode.
- Header aliases identical to `SALES_COLUMNS`. Required: CustomerName, Product, Amount and Month + Year (or Date).
- Row rules identical (skip blank rows; collect warnings; `currency` empty → `N/A`).
- Insert the upload, records and issues in **one transaction**; resolve `dealer_id` / `product_id` /
  `country_id` / `currency_id` by name match where possible.
- Store the original file through `StorageService` (needed for audit / re-processing).
- Very large files (> ~50k rows): process in a background task and poll `status`.

**Forecasting** (port of `lib/salesForecast.js`; must match the UI):
- Monthly continuous series; model selection 24+ months → Holt-Winters additive; 6–23 → SES / Holt /
  damped Holt by lowest AICc; 3–5 → OLS trend; otherwise `insufficient` with the same reasons.
- 95% bounds from one-step residual σ; scenarios = 16th / 84th percentile of 2,000 simulated
  12-month totals. Reuse the **same seeded PRNG (mulberry32 + Box-Muller)**, seeded from the same
  `period:value|…` string with numbers formatted as JavaScript prints them (e.g. `742428`, not
  `742428.0`), so Python and JavaScript return identical numbers.
- Parity target on `sample_sales.xlsx` (All currencies → USD): SES α = 0.4, base 12-month total
  1,663,490, conservative 485,974, optimistic 4,340,990, growth −6.2%.

## 7. Configuration

`backend/.env` (never committed; `.env` is already in `.gitignore`):

```dotenv
DATABASE_URL=postgresql+psycopg://dcp_app:<url-encoded-password>@<host>:5432/postgres?sslmode=require
DB_SCHEMA=dcp
JWT_SECRET=<64+ random bytes>
ACCESS_TOKEN_MINUTES=15
REFRESH_TOKEN_DAYS_REMEMBER=30
REFRESH_TOKEN_HOURS=12
COOKIE_SECURE=true
STORAGE_BACKEND=supabase          # supabase | s3 | local
STORAGE_BUCKET=dcp-files
MAX_UPLOAD_MB=10
FRONTEND_ORIGIN=http://localhost:3000
```

**Supabase connection notes**
- **Encode special characters in the password.** In a connection URL, `@` must be written as `%40`,
  `:` as `%3A`, `/` as `%2F`, and so on. A password containing `@` breaks URL parsing otherwise.
- Use the direct connection (port 5432) or the **session** pooler for migrations and the app. With
  the **transaction** pooler (port 6543), disable prepared statements (`prepare_threshold=None`).
- Always connect with `sslmode=require`.
- **Don't run the app as `postgres`.** Create a dedicated role:
  ```sql
  CREATE ROLE dcp_app LOGIN PASSWORD '<strong password>';
  GRANT USAGE ON SCHEMA dcp TO dcp_app;
  GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA dcp TO dcp_app;
  GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA dcp TO dcp_app;
  ALTER DEFAULT PRIVILEGES IN SCHEMA dcp GRANT SELECT, INSERT, UPDATE ON TABLES TO dcp_app;
  ALTER DEFAULT PRIVILEGES IN SCHEMA dcp GRANT USAGE, SELECT ON SEQUENCES TO dcp_app;
  ```
  (No `DELETE`: soft delete only.)
- If schema `dcp` is ever exposed through the Supabase Data API, enable Row Level Security on every table first.

## 8. Frontend changes (when the API is ready)

1. Add `rewrites()` in `next.config.mjs`: `/api/v1/:path*` → `${API_ORIGIN}/api/v1/:path*`.
2. Replace the bodies of `src/services/*.js` with `fetch('/api/v1/...')` calls through one small
   client helper that sends the `X-CSRF-Token` header and retries once via `/auth/refresh` on 401.
   Keep the method names and return shapes.
3. Delete the mock auth routes (`src/app/api/auth/*`, `src/lib/server/session.js`) and `src/lib/mockApi.js`.
4. Change `src/proxy.js` to check for the `dcp_access` / `dcp_refresh` cookies instead of verifying the mock HMAC.
5. Communications: refetch after send, instead of using the in-memory `subscribe`.
6. Settings: load and save `/users/me/settings`; keep "Simulate API errors" as a dev-only toggle.
7. Sales: the Redux slice stays the in-page workspace; thunks call `/sales/uploads`. Add a "Recent uploads" picker (see open question 2).

## 9. Testing strategy

| Level | What |
|---|---|
| Unit | Sales parsing rules, sector matching, filter → SQL builder, forecasting maths |
| Parity | Same inputs as the JS versions must give the same outputs: dealer filters (India+North+Active = 3; India/Germany + North/South + Active = 7; Electrical + Switchgear = 18) and the forecast numbers in §6 |
| API / integration | httpx against a real PostgreSQL (disposable cluster or Testcontainers) loaded with `02_schema.sql` + `03_seed.sql`; auth flows, tenant isolation (company A can't read company B), validation errors, upload limits |
| Contract | Snapshot the JSON shapes the frontend reads (dealer, communication, sales upload) |
| Security | Login lockout, CSRF header required, file-type spoofing rejected, SQL injection attempts through search/filters |

## 10. Delivery phases

| Phase | Deliverables | Size |
|---|---|---|
| 0. Foundations | Repo setup, config, DB session, Alembic baseline from `02_schema.sql`, seed, `/health`, CI (ruff + pytest) | S |
| 1. Auth & users | Login/logout/session/refresh, Argon2, lockout, `/users/me`, settings, CLI `set-password`, Next.js rewrite + proxy change | M |
| 2. Dealers | List with filters, facets and pagination, details, search, recent, lookups, dashboard stats, company + sector endpoints. Frontend dealer/company services switched | M |
| 3. Communication | History, recent, stats, send message with attachment (storage), log interaction. Frontend switched | M |
| 4. Sales upload | Server-side parsing + persistence, uploads list/reopen/delete, exchange rates. Redux thunks switched | M |
| 5. Analytics & forecast | Python ports with parity tests; `/sales/analytics`, `/sales/forecast`; optional move of calculations off the browser | M |
| 6. Hardening | Rate limiting, audit review, logging/monitoring, Docker image, deployment, load test of dealer list | S–M |

## 11. Database setup steps

```bash
# Self-hosted PostgreSQL only (skip on Supabase)
psql "postgresql://postgres@localhost:5432/postgres" -v ON_ERROR_STOP=1 -f database/01_create_database.sql

# Schema + seed (Supabase: use the project's connection string)
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/02_schema.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/03_seed.sql

# Regenerate seed / ERD after data or schema changes
python database/generate_seed.py
python database/generate_erd.py      # needs DATABASE_URL
```

Both SQL scripts are idempotent (safe to re-run). They were verified on PostgreSQL 18 (27 tables after migration 0002), all
with the six common columns and a `modified_on` trigger; seed loads 40 sectors, 553 sub-sectors,
57 dealers, 35 products and 256 dealer–product links.

## 12. Open questions / decisions for the product owner

1. **Dealer ownership:** should each company keep its own dealer list (current design), or should
   there be one shared dealer directory linked to companies through a mapping table?
2. **Sales data lifetime:** today a browser refresh clears uploaded sales (requirement). With a
   backend, uploads are saved. Should the page reopen the latest upload automatically, offer a
   "Recent uploads" list, or keep the refresh-clears behaviour (and delete uploads after a session)?
3. **Message delivery:** "Send Message" only records the message today. Should it also send an
   email or notification (and through which provider: SendGrid, SES, SMTP)?
4. **Sales ↔ dealers:** the sample sales customers don't match any dealer. Should uploads be
   restricted to known dealers, or is name matching (with manual linking) enough?
5. **Supabase Auth vs own auth:** this plan uses its own `users` / `user_sessions` tables as requested.
   Supabase Auth could replace them (and provide SSO/MFA), but then user ids would be UUIDs.
6. **Column naming:** confirm `snake_case` (recommended) rather than quoted `PascalCase`.
7. **Attachment storage:** Supabase Storage, S3 or another store, and the retention period.
