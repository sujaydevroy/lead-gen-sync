"""Declarative base + the common audit columns shared by every table."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Identity, MetaData, event, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.core.config import SCHEMA


class Base(DeclarativeBase):
    metadata = MetaData(schema=SCHEMA)


class AuditMixin:
    """Id, IsActive, CreatedBy, CreatedOn, ModifiedBy, ModifiedOn (see database/02_schema.sql)."""

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"), default=True)
    created_by: Mapped[int | None] = mapped_column(BigInteger)
    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    modified_by: Mapped[int | None] = mapped_column(BigInteger)
    modified_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


@event.listens_for(Session, "before_flush")
def _fill_audit_columns(session: Session, _flush_context, _instances) -> None:
    """Stamp created_by / modified_by with the authenticated user (set in session.info by the auth dependency)."""
    user_id = session.info.get("user_id")
    if user_id is None:
        return
    for obj in session.new:
        if isinstance(obj, AuditMixin):
            if obj.created_by is None:
                obj.created_by = user_id
            obj.modified_by = user_id
    for obj in session.dirty:
        if isinstance(obj, AuditMixin) and session.is_modified(obj, include_collections=False):
            obj.modified_by = user_id
