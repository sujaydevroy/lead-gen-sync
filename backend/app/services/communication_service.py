"""Communication history, sending messages (with attachments) and logging interactions."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import PurePath

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ApiError, not_found
from app.models import (
    Communication,
    CommunicationAttachment,
    CommunicationStatus,
    CommunicationType,
    Company,
    Dealer,
    User,
)
from app.repositories.dealer_repository import escape_like
from app.schemas.common import Page
from app.schemas.communication import AttachmentOut, CommunicationOut, CommunicationStats
from app.services import dealer_service
from app.services.storage_service import build_key, get_storage, safe_file_name

ALLOWED_ATTACHMENT_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".png", ".jpg", ".jpeg", ".txt"}
SUBJECT_RANGE = (3, 150)
MESSAGE_RANGE = (10, 5000)


@dataclass
class IncomingFile:
    name: str
    content_type: str | None
    content: bytes


def dealer_party(dealer: Dealer) -> str:
    return f"{dealer.contact_person} ({dealer.dealer_name})" if dealer.contact_person else dealer.dealer_name


def to_out(item: Communication) -> CommunicationOut:
    recipient = item.recipient_name + (f" <{item.recipient_email}>" if item.recipient_email else "")
    return CommunicationOut(
        id=f"COM-{item.id}",
        dealer_id=item.dealer.dealer_code,
        dealer_name=item.dealer.dealer_name,
        type=item.type.name,
        direction=item.direction,
        sender=item.sender_name,
        recipient=recipient,
        subject=item.subject,
        body=item.body,
        status=item.status.name,
        created_at=item.occurred_on,
        attachments=[
            AttachmentOut(
                id=a.id,
                name=a.file_name,
                size=a.size_bytes,
                type=a.content_type,
                url=f"/api/v1/communications/{item.id}/attachments/{a.id}",
            )
            for a in item.attachments
        ],
    )


def _lookup_id(db: Session, model, name: str) -> int:
    value = db.scalar(select(model.id).where(model.name == name))
    if value is None:
        raise ApiError(500, f"Reference data missing: {model.__tablename__} '{name}'. Run the seed script.")
    return value


def _scope(company: Company):
    return [Communication.company_id == company.id, Communication.is_active]


def list_communications(
    db: Session,
    company: Company,
    *,
    dealer_code: str | None,
    types: list[str],
    direction: str | None,
    search: str,
    page: int,
    page_size: int,
) -> Page[CommunicationOut]:
    conditions = _scope(company)
    if dealer_code:
        dealer = dealer_service.get_dealer(db, company, dealer_code)
        conditions.append(Communication.dealer_id == dealer.id)
    if types:
        conditions.append(
            Communication.communication_type_id.in_(select(CommunicationType.id).where(CommunicationType.name.in_(types)))
        )
    if direction:
        conditions.append(Communication.direction == direction)
    term = (search or "").strip()
    if term:
        pattern = f"%{escape_like(term)}%"
        conditions.append(
            or_(
                *(
                    col.ilike(pattern, escape="\\")
                    for col in (
                        Communication.subject,
                        Communication.sender_name,
                        Communication.recipient_name,
                        Communication.body,
                    )
                ),
                Communication.dealer_id.in_(
                    select(Dealer.id).where(
                        or_(Dealer.dealer_name.ilike(pattern, escape="\\"), Dealer.dealer_code.ilike(pattern, escape="\\"))
                    )
                ),
            )
        )

    total = db.scalar(select(func.count(Communication.id)).where(*conditions)) or 0
    total_pages = max(1, math.ceil(total / page_size))
    page = min(max(1, page), total_pages)
    rows = db.scalars(
        select(Communication)
        .where(*conditions)
        .order_by(Communication.occurred_on.desc(), Communication.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).unique()
    return Page[CommunicationOut](
        items=[to_out(r) for r in rows], total=total, page=page, page_size=page_size, total_pages=total_pages
    )


def recent_communications(db: Session, company: Company, limit: int) -> list[CommunicationOut]:
    rows = db.scalars(
        select(Communication)
        .where(*_scope(company))
        .order_by(Communication.occurred_on.desc(), Communication.id.desc())
        .limit(limit)
    ).unique()
    return [to_out(r) for r in rows]


def communication_stats(db: Session, company: Company) -> CommunicationStats:
    messaging = select(CommunicationType.id).where(CommunicationType.name.in_(["Email", "Message"]))

    def count(*extra):
        return db.scalar(select(func.count(Communication.id)).where(*_scope(company), *extra)) or 0

    return CommunicationStats(
        sent=count(Communication.direction == "outbound", Communication.communication_type_id.in_(messaging)),
        received=count(Communication.direction == "inbound", Communication.communication_type_id.in_(messaging)),
        total=count(),
    )


def _validate_text(label: str, value: str, bounds: tuple[int, int]) -> str:
    value = (value or "").strip()
    low, high = bounds
    if len(value) < low:
        raise ApiError(422, f"{label} must be at least {low} characters.")
    if len(value) > high:
        raise ApiError(422, f"{label} must be {high:,} characters or fewer.")
    return value


def _validate_attachment(file: IncomingFile) -> None:
    extension = PurePath(file.name).suffix.lower()
    if extension not in ALLOWED_ATTACHMENT_EXTENSIONS:
        raise ApiError(422, "Attachment type is not allowed. Use PDF, Office, image or text files.")
    if len(file.content) > get_settings().max_upload_bytes:
        raise ApiError(413, f"Attachment must be {get_settings().max_upload_mb} MB or smaller.")
    if not file.content:
        raise ApiError(422, "Attachment is empty.")


def send_message(
    db: Session, company: Company, user: User, dealer_code: str, *, subject: str, message: str, attachment: IncomingFile | None
) -> CommunicationOut:
    subject = _validate_text("Subject", subject, SUBJECT_RANGE)
    message = _validate_text("Message", message, MESSAGE_RANGE)
    dealer = dealer_service.get_dealer(db, company, dealer_code)
    if attachment is not None:
        _validate_attachment(attachment)

    item = Communication(
        company_id=company.id,
        dealer_id=dealer.id,
        communication_type_id=_lookup_id(db, CommunicationType, "Message"),
        communication_status_id=_lookup_id(db, CommunicationStatus, "Sent"),
        direction="outbound",
        sender_user_id=user.id,
        sender_name=user.full_name,
        recipient_name=dealer_party(dealer),
        recipient_email=dealer.email,
        subject=subject,
        body=message,
    )
    db.add(item)
    db.flush()
    if attachment is not None:
        key = build_key(company.company_code, "attachments", file_name=attachment.name)
        get_storage().save(key, attachment.content)
        db.add(
            CommunicationAttachment(
                communication_id=item.id,
                file_name=safe_file_name(attachment.name),
                content_type=(attachment.content_type or "application/octet-stream")[:150],
                size_bytes=len(attachment.content),
                storage_path=key,
            )
        )
    db.commit()
    return to_out(_reload(db, item.id))


def log_interaction(db: Session, company: Company, user: User, dealer_code: str, *, kind: str, subject: str) -> CommunicationOut:
    dealer = dealer_service.get_dealer(db, company, dealer_code)
    body = f"Call started to {dealer.phone}" if kind == "Call" else f"Email draft opened to {dealer.email}"
    item = Communication(
        company_id=company.id,
        dealer_id=dealer.id,
        communication_type_id=_lookup_id(db, CommunicationType, kind),
        communication_status_id=_lookup_id(db, CommunicationStatus, "Initiated"),
        direction="outbound",
        sender_user_id=user.id,
        sender_name=user.full_name,
        recipient_name=dealer_party(dealer),
        recipient_email=None,
        subject=subject,
        body=body,
    )
    db.add(item)
    db.commit()
    return to_out(_reload(db, item.id))


def _reload(db: Session, communication_id: int) -> Communication:
    db.expire_all()
    return db.get(Communication, communication_id)


def get_attachment(
    db: Session, company: Company, communication_id: int, attachment_id: int
) -> tuple[CommunicationAttachment, bytes]:
    attachment = db.scalar(
        select(CommunicationAttachment)
        .join(Communication, Communication.id == CommunicationAttachment.communication_id)
        .where(
            CommunicationAttachment.id == attachment_id,
            CommunicationAttachment.communication_id == communication_id,
            CommunicationAttachment.is_active,
            *_scope(company),
        )
    )
    if attachment is None:
        raise not_found("Attachment")
    storage = get_storage()
    if not storage.exists(attachment.storage_path):
        raise not_found("Attachment file")
    return attachment, storage.read(attachment.storage_path)
