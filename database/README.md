# Database scripts

PostgreSQL schema for the Dealer Communication Portal. Background and design decisions:
[`docs/backend/BACKEND_PLAN.md`](../docs/backend/BACKEND_PLAN.md) · diagram: [`docs/backend/ERD.md`](../docs/backend/ERD.md).

| File | Purpose |
|---|---|
| `01_create_database.sql` | Creates database `dealer_portal`. **Self-hosted only**; skip on Supabase |
| `02_schema.sql` | Complete current schema `dcp`: 27 tables, constraints, indexes, `modified_on` triggers |
| `migrations/0002_sales_upload_detail.sql` | Upgrade for databases created before the sales master/detail tables (idempotent; run by Alembic / `python -m app.cli setup`) |
| `03_seed.sql` | Lookups, sectors/sub-sectors, company, admin user, 57 dealers (**generated**) |
| `generate_seed.py` | Rebuilds `03_seed.sql` from `sector.json` + `dealers.json` |
| `generate_erd.py` | Rebuilds `docs/backend/ERD.md` + `erd.html` from a live database (`DATABASE_URL`) |

## Run

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/02_schema.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/03_seed.sql
```

Both scripts are idempotent. Put the connection string in an environment variable rather than on the
command line, and URL-encode special characters in the password (`@` → `%40`).

Every table has the common columns `id`, `is_active`, `created_by`, `created_on`, `modified_by`,
`modified_on` (PostgreSQL equivalents of `Id`, `IsActive`, `CreatedBy`, `CreatedOn`, `ModifiedBy`,
`ModifiedOn`). The seeded user (`john.smith@abc.com`) has no password until one is set through the
backend CLI.

## Sales upload storage (master / detail)

| Table | Holds |
|---|---|
| `dcp.sales_uploads` (master) | One row per uploaded workbook: display + original file name, sheet name, size, SHA-256, `storage_path` (location in the storage backend) and `physical_path` (absolute path on the API server), row/column counts |
| `dcp.sales_upload_columns` | One row per sheet column: position (1 = A), letter, header text, `data_key`, recognised field |
| `dcp.sales_upload_rows` | One row per sheet data row: Excel row number, **all cells** as JSONB (`row_data`), `is_valid`, link to the typed row |
| `dcp.sales_records` | Typed, validated rows used by analytics |
| `dcp.sales_upload_issues` | Why rows were skipped / warnings |

Example: all cells of one upload in sheet order

```sql
select r.row_number, r.is_valid, c.column_letter, c.header_name, r.row_data ->> c.data_key as value
from dcp.sales_upload_rows r
join dcp.sales_upload_columns c on c.sales_upload_id = r.sales_upload_id
where r.sales_upload_id = 1
order by r.row_number, c.column_index;
```
