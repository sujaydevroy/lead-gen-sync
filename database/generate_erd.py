"""Generate the ERD (Mermaid) from a database that has database/02_schema.sql applied.

Reads the catalog of schema "dcp" and writes:
    ERD.md    - Mermaid diagrams (render in GitHub / VS Code Markdown preview)
    erd.html  - same diagrams, viewable in any browser

Usage (connection string from the environment, never hard-coded):
    set DATABASE_URL=postgresql://user:password@host:5432/dbname      (Windows)
    export DATABASE_URL=postgresql://user:password@host:5432/dbname   (macOS / Linux)
    python database/generate_erd.py
"""

from __future__ import annotations

import html
import os
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT
SCHEMA = "dcp"
COMMON = ["id", "is_active", "created_by", "created_on", "modified_by", "modified_on"]

GROUPS = [
    ("Reference data", ["roles", "countries", "regions", "currencies", "dealer_types", "dealer_statuses",
                        "communication_types", "communication_statuses", "sectors", "sub_sectors"]),
    ("Company, users & auth", ["companies", "users", "user_settings", "user_sessions", "password_reset_tokens"]),
    ("Dealers & products", ["dealers", "products", "product_sub_sectors", "dealer_products"]),
    ("Communication", ["communications", "communication_attachments"]),
    ("Sales", ["sales_uploads", "sales_upload_columns", "sales_upload_rows", "sales_upload_issues", "sales_records", "exchange_rates"]),
]

TYPE_NAMES = {
    "bigint": "bigint", "integer": "int", "smallint": "smallint", "boolean": "boolean", "text": "text",
    "character varying": "varchar", "character": "char", "numeric": "numeric", "date": "date",
    "timestamp with time zone": "timestamptz", "inet": "inet", "jsonb": "jsonb",
}


def fetch(conn):
    columns = conn.execute(
        """
        SELECT table_name, column_name, data_type, character_maximum_length, numeric_precision,
               numeric_scale, is_nullable, ordinal_position
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name <> 'alembic_version'
        ORDER BY table_name, ordinal_position
        """,
        (SCHEMA,),
    ).fetchall()
    fks = conn.execute(
        """
        SELECT tc.table_name, kcu.column_name, ccu.table_name AS ref_table
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON kcu.constraint_name = tc.constraint_name AND kcu.table_schema = tc.table_schema
        JOIN information_schema.constraint_column_usage ccu
          ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
        WHERE tc.table_schema = %s AND tc.constraint_type = 'FOREIGN KEY'
        """,
        (SCHEMA,),
    ).fetchall()
    # Single-column unique constraints / unique indexes (to mark UK and detect 1:1 relations)
    uniques = conn.execute(
        """
        SELECT t.relname, a.attname
        FROM pg_index i
        JOIN pg_class t ON t.oid = i.indrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = i.indkey[0]
        WHERE n.nspname = %s AND i.indisunique AND NOT i.indisprimary
          AND i.indnatts = 1 AND i.indpred IS NULL
        """,
        (SCHEMA,),
    ).fetchall()
    return columns, fks, {(t, c) for t, c in uniques}


def column_type(data_type, length, precision, scale):
    name = TYPE_NAMES.get(data_type, data_type.replace(" ", "_"))
    if data_type in ("character varying", "character") and length:
        return f"{name}_{length}"
    if data_type == "numeric" and precision:
        return f"numeric_{precision}_{scale}"
    return name


def build(columns, fks, uniques):
    fk_map = {(t, c): ref for t, c, ref in fks}
    tables: dict[str, list[str]] = {}
    nullable: dict[tuple[str, str], bool] = {}
    for table, col, dtype, length, precision, scale, is_nullable, _ in columns:
        nullable[(table, col)] = is_nullable == "YES"
        keys = []
        if col == "id":
            keys.append("PK")
        if (table, col) in fk_map:
            keys.append("FK")
        if (table, col) in uniques and col != "id":
            keys.append("UK")
        key = f" {', '.join(keys)}" if keys else ""
        note = ' "audit"' if col in COMMON[1:] else ""
        tables.setdefault(table, []).append(f"        {column_type(dtype, length, precision, scale)} {col}{key}{note}")

    relations = []
    for table, col, ref in sorted(fks):
        child = "o|" if (table, col) in uniques else "o{"
        parent = "|o" if nullable[(table, col)] else "||"
        relations.append(f'    {ref} {parent}--{child} {table} : "{col}"')
    return tables, relations


def diagrams(tables, relations):
    overview = ["erDiagram", *relations]
    full = ["erDiagram"]
    for _, names in GROUPS:
        for name in names:
            if name in tables:
                full.append(f"    {name} {{")
                full.extend(tables[name])
                full.append("    }")
    full.extend(relations)
    return "\n".join(overview), "\n".join(full)


def write(overview, full, table_count, fk_count):
    group_lines = "\n".join(f"| {title} | {', '.join(f'`{n}`' for n in names)} |" for title, names in GROUPS)
    md = f"""# Dealer Communication Portal — ERD

Generated by `database/generate_erd.py` from the `{SCHEMA}` schema created by `database/02_schema.sql`
({table_count} tables, {fk_count} foreign keys). Re-run the generator after schema changes.

**Every table** has the common columns `id` (bigint PK), `is_active`, `created_by`, `created_on`,
`modified_by`, `modified_on` (marked `audit` below). `created_by` / `modified_by` hold a user id but
are deliberately not foreign keys, so they are not drawn as relationships.

Type suffixes: `varchar_200` = `VARCHAR(200)`, `numeric_18_2` = `NUMERIC(18,2)`.
Relationship lines: `||` required parent, `|o` optional parent, `o{{` many children, `o|` at most one child.

| Area | Tables |
|---|---|
{group_lines}

## 1. Relationships overview

```mermaid
{overview}
```

## 2. Full diagram (all columns)

```mermaid
{full}
```
"""
    (DOCS / "ERD.md").write_text(md, encoding="utf-8")

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dealer Portal ERD</title>
<style>
  :root {{ --bg: #f4f6fa; --card: #ffffff; --text: #0f1e3c; --muted: #52607a; --border: #e3e8ef; }}
  body {{ margin: 0; background: var(--bg); color: var(--text); font: 15px/1.5 "Segoe UI", system-ui, sans-serif; }}
  main {{ max-width: 1600px; margin: 0 auto; padding: 24px 16px 48px; }}
  h1 {{ font-size: 1.5rem; margin: 0 0 4px; }}
  p {{ color: var(--muted); margin: 0 0 16px; }}
  section {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 16px; margin-top: 16px; overflow-x: auto; }}
  h2 {{ font-size: 1.1rem; margin: 0 0 12px; }}
</style>
</head>
<body>
<main>
  <h1>Dealer Communication Portal — ERD</h1>
  <p>{table_count} tables in schema <code>{SCHEMA}</code>. Every table also has the common columns
     id, is_active, created_by, created_on, modified_by, modified_on.</p>
  <section><h2>1. Relationships overview</h2><pre class="mermaid">{html.escape(overview)}</pre></section>
  <section><h2>2. Full diagram (all columns)</h2><pre class="mermaid">{html.escape(full)}</pre></section>
</main>
<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
  mermaid.initialize({{ startOnLoad: true, theme: 'neutral', er: {{ useMaxWidth: false }} }});
</script>
</body>
</html>
"""
    (DOCS / "erd.html").write_text(page, encoding="utf-8")


def main() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("Set DATABASE_URL to a database where database/02_schema.sql has been applied.")
    DOCS.mkdir(parents=True, exist_ok=True)
    with psycopg.connect(url) as conn:
        columns, fks, uniques = fetch(conn)
    tables, relations = build(columns, fks, uniques)
    overview, full = diagrams(tables, relations)
    write(overview, full, len(tables), len(relations))
    print(f"Wrote ERD.md and erd.html ({len(tables)} tables, {len(relations)} relationships)")


if __name__ == "__main__":
    main()
