# CLAUDE.md — lead-gen-sync (DealerConnect)

Read **`HANDOFF.md`** first: current state, how to run, how to test safely, decisions and gotchas.

## Essentials

- Frontend: Next.js 16 + React 19 + **JavaScript** + MUI 9 (`frontend/`: `frontend/src/`, `frontend/public/`; run npm commands from `frontend/`). Backend: FastAPI + SQLAlchemy 2
  (sync) + Alembic (`backend/`, venv at `backend/.venv`). Database: Supabase PostgreSQL, schema `dcp`.
- Run: `.claude/launch.json` configs `portal-dev` (:3000) and `api-dev` (:8000). Backend commands run from
  `backend/` with `.venv\Scripts\python ...`.
- Database changes: add an idempotent SQL file in `database/migrations/` + an Alembic revision, and update
  `database/02_schema.sql` to the full current schema. Every table gets the six common columns
  (`id, is_active, created_by, created_on, modified_by, modified_on`) and a `modified_on` trigger.
  Regenerate the ERD with `database/generate_erd.py` against a throwaway DB.
- Test against a **throwaway local PostgreSQL on port 55432**, never the user's Supabase DB or their local
  server on 5432. Backend: `pytest` with `TEST_DATABASE_URL` (DB name must end in `_test`). Frontend: `npx next build` (from `frontend/`).
- Keep API response shapes identical to what `frontend/src/services/*.js` expect; keep the Python analytics/forecast in
  parity with `frontend/src/lib/salesAnalytics.js` / `salesForecast.js`.

## Working with this user

- Never commit or push without explicit permission in the current message; show `git diff --stat` and ask.
- Put everything important in the **final message** of a turn (text between tool calls isn't seen).
- New to Python: give exact PowerShell commands, one per code block, and say which folder to run them in.
- Never read or print `backend/.env` / `frontend/.env.local` secrets.
