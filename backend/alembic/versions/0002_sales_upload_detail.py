"""Sales upload master/detail: physical file details + per-column and per-row storage

Runs database/migrations/0002_sales_upload_detail.sql (idempotent).
After upgrading, `python -m app.cli backfill-sales-uploads` fills the new tables for workbooks
uploaded before this migration (`python -m app.cli setup` does that automatically).

Revision ID: 0002_sales_upload_detail
Revises: 0001_baseline
Create Date: 2026-10-08
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

from app.core.database import run_sql_script

revision = "0002_sales_upload_detail"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None

MIGRATION_SQL = Path(__file__).resolve().parents[3] / "database" / "migrations" / "0002_sales_upload_detail.sql"


def upgrade() -> None:
    run_sql_script(op.get_bind(), MIGRATION_SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS dcp.sales_upload_rows")
    op.execute("DROP TABLE IF EXISTS dcp.sales_upload_columns")
    for column in (
        "original_file_name",
        "sheet_name",
        "content_type",
        "file_sha256",
        "storage_backend",
        "physical_path",
        "column_count",
    ):
        op.execute(f"ALTER TABLE dcp.sales_uploads DROP COLUMN IF EXISTS {column}")
