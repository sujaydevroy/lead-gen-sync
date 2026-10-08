"""System administration: System Administrator role and platform company flag

Runs database/migrations/0003_admin_dealer_uploads.sql (idempotent).
(The revision id keeps its original name; the dealer upload table it once created is removed by 0004.)
Create a system administrator afterwards with `python -m app.cli create-sysadmin <email>`.

Revision ID: 0003_admin_dealer_uploads
Revises: 0002_sales_upload_detail
Create Date: 2026-10-08
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

from app.core.database import run_sql_script

revision = "0003_admin_dealer_uploads"
down_revision = "0002_sales_upload_detail"
branch_labels = None
depends_on = None

MIGRATION_SQL = Path(__file__).resolve().parents[3] / "database" / "migrations" / "0003_admin_dealer_uploads.sql"


def upgrade() -> None:
    run_sql_script(op.get_bind(), MIGRATION_SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    op.execute("ALTER TABLE dcp.companies DROP COLUMN IF EXISTS is_platform")
    # The role row stays if users still reference it; otherwise remove it.
    op.execute(
        "DELETE FROM dcp.roles r WHERE r.name = 'System Administrator' "
        "AND NOT EXISTS (SELECT 1 FROM dcp.users u WHERE u.role_id = r.id)"
    )
