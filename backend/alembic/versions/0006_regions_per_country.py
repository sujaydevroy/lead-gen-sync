"""Regions per country (+ India North East), dealer sources, trade-channel dealer types

Runs database/migrations/0006_regions_per_country_dealer_sources.sql (idempotent).

Revision ID: 0006_regions_per_country
Revises: 0005_dealers_drop_company
Create Date: 2026-10-08
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

from app.core.database import run_sql_script

revision = "0006_regions_per_country"
down_revision = "0005_dealers_drop_company"
branch_labels = None
depends_on = None

MIGRATION_SQL = Path(__file__).resolve().parents[3] / "database" / "migrations" / "0006_regions_per_country_dealer_sources.sql"


def upgrade() -> None:
    run_sql_script(op.get_bind(), MIGRATION_SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    pass  # regions stay per country; dealer sources are kept
