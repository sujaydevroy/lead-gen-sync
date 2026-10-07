from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditMixin, Base
from app.models.dealer import Dealer
from app.models.lookups import CommunicationStatus, CommunicationType


class Communication(AuditMixin, Base):
    __tablename__ = "communications"
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("dcp.companies.id"))
    dealer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("dcp.dealers.id"))
    communication_type_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("dcp.communication_types.id"))
    communication_status_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("dcp.communication_statuses.id"))
    direction: Mapped[str] = mapped_column(String(10))
    sender_user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("dcp.users.id"))
    sender_name: Mapped[str] = mapped_column(String(200))
    recipient_name: Mapped[str] = mapped_column(String(200))
    recipient_email: Mapped[str | None] = mapped_column(String(254))
    subject: Mapped[str] = mapped_column(String(200))
    body: Mapped[str | None] = mapped_column(Text)
    occurred_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    dealer: Mapped[Dealer] = relationship(lazy="joined")
    type: Mapped[CommunicationType] = relationship(lazy="joined")
    status: Mapped[CommunicationStatus] = relationship(lazy="joined")
    attachments: Mapped[list[CommunicationAttachment]] = relationship(
        lazy="selectin",
        primaryjoin="and_(Communication.id == CommunicationAttachment.communication_id, CommunicationAttachment.is_active)",
        viewonly=True,
    )


class CommunicationAttachment(AuditMixin, Base):
    __tablename__ = "communication_attachments"
    communication_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("dcp.communications.id"))
    file_name: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str | None] = mapped_column(String(150))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    storage_path: Mapped[str] = mapped_column(String(500))
