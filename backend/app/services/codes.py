"""Next public codes (CMP-10046, USR-2003, DLR-1058, ...) from the highest number already used."""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import InstrumentedAttribute, Session


def highest_number(codes, prefix: str) -> int:
    pattern = re.compile(rf"^{re.escape(prefix)}-(\d+)$", re.IGNORECASE)
    numbers = [int(m.group(1)) for code in codes if code and (m := pattern.match(code.strip()))]
    return max(numbers, default=0)


def next_code(db: Session, column: InstrumentedAttribute, prefix: str, *, start: int, where=None) -> str:
    stmt = select(column).where(column.ilike(f"{prefix}-%"))
    if where is not None:
        stmt = stmt.where(where)
    return f"{prefix}-{max(highest_number(db.scalars(stmt), prefix) + 1, start)}"
