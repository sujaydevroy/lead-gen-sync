"""Dealers belong to no company: drop dcp.dealers.company_id, Dealer ID unique system-wide

Runs database/migrations/0005_dealers_drop_company.sql (idempotent).

Revision ID: 0005_dealers_drop_company
Revises: 0004_drop_dealer_uploads
Create Date: 2026-10-08
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

from app.core.database import run_sql_script

revision = "0005_dealers_drop_company"
down_revision = "0004_drop_dealer_uploads"
branch_labels = None
depends_on = None

MIGRATION_SQL = Path(__file__).resolve().parents[3] / "database" / "migrations" / "0005_dealers_drop_company.sql"


def upgrade() -> None:
    run_sql_script(op.get_bind(), MIGRATION_SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    pass  # dealers are not reassigned to companies
