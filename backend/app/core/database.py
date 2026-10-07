"""Database engine and request-scoped sessions (SQLAlchemy 2.0, psycopg 3, sync)."""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Connection, Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    # All tables are schema-qualified (dcp.*), so no search_path startup option is needed —
    # connection poolers such as Supabase's Supavisor may reject startup options.
    connect_args: dict = {"connect_timeout": 15}
    if settings.db_disable_prepared_statements:
        connect_args["prepare_threshold"] = None
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        connect_args=connect_args,
    )


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def run_sql_script(connection: Connection, sql: str) -> None:
    """Execute a multi-statement SQL script verbatim inside the connection's current transaction.

    Goes through the raw psycopg cursor without parameters, so '%' characters in the script
    (e.g. format('%1$s') in PL/pgSQL) are not treated as bind placeholders. The script's own
    BEGIN / COMMIT lines are removed because the caller controls the transaction.
    """
    body = "\n".join(line for line in sql.splitlines() if line.strip().upper() not in ("BEGIN;", "COMMIT;"))
    with connection.connection.dbapi_connection.cursor() as cursor:
        cursor.execute(body)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, rolled back on error."""
    session = get_session_factory()()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
