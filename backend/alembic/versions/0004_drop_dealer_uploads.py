"""Remove dcp.dealer_uploads: dealer files are saved only in dcp.dealers and its product tables

Runs database/migrations/0004_drop_dealer_uploads.sql (idempotent).

Revision ID: 0004_drop_dealer_uploads
Revises: 0003_admin_dealer_uploads
Create Date: 2026-10-08
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

from app.core.database import run_sql_script

revision = "0004_drop_dealer_uploads"
down_revision = "0003_admin_dealer_uploads"
branch_labels = None
depends_on = None

MIGRATION_SQL = Path(__file__).resolve().parents[3] / "database" / "migrations" / "0004_drop_dealer_uploads.sql"


def upgrade() -> None:
    run_sql_script(op.get_bind(), MIGRATION_SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    pass  # the upload log table is not recreated
