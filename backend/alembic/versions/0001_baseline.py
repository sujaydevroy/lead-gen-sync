"""Baseline: create the dcp schema from database/02_schema.sql

If the schema was already created by running the SQL script with psql, mark it as applied with:
    alembic stamp 0001_baseline

Revision ID: 0001_baseline
Revises:
Create Date: 2026-10-07
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

from app.core.database import run_sql_script

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None

SCHEMA_SQL = Path(__file__).resolve().parents[3] / "database" / "02_schema.sql"


def upgrade() -> None:
    # Alembic already runs the migration in a transaction; run_sql_script drops the script's BEGIN/COMMIT.
    run_sql_script(op.get_bind(), SCHEMA_SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError("The baseline cannot be downgraded automatically. Drop schema dcp manually if intended.")
