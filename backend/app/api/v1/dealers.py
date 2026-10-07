from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_auth
from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import ApiError
from app.schemas.communication import CommunicationOut, InteractionCreate
from app.schemas.dealer import DealerFilters, DealerListResponse, DealerOut
from app.services import communication_service, dealer_service

router = APIRouter(prefix="/dealers", tags=["dealers"])


@router.get("", response_model=DealerListResponse)
def list_dealers(
    search: str = Query("", max_length=200),
    countries: list[str] = Query(default=[]),
    regions: list[str] = Query(default=[]),
    statuses: list[str] = Query(default=[]),
    types: list[str] = Query(default=[]),
    sectors: list[str] = Query(default=[]),
    sub_sectors: list[str] = Query(default=[], alias="subSectors"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize"),
    auth: AuthContext = Depends(get_auth),
    db: Session = Depends(get_db),
):
    """Search + filters (repeat a parameter for multiple values) + facets + server-side pagination."""
    filters = DealerFilters(
        countries=countries, regions=regions, statuses=statuses, types=types, sectors=sectors, sub_sectors=sub_sectors
    )
    return dealer_service.list_dealers(db, auth.company, search=search, filters=filters, page=page, page_size=page_size)


@router.get("/search", response_model=list[DealerOut])
def search_dealers(
    q: str = Query("", max_length=200),
    limit: int = Query(20, ge=1, le=50),
    auth: AuthContext = Depends(get_auth),
    db: Session = Depends(get_db),
):
    return dealer_service.search_dealers(db, auth.company, q, limit)


@router.get("/recent", response_model=list[DealerOut])
def recent_dealers(limit: int = Query(5, ge=1, le=50), auth: AuthContext = Depends(get_auth), db: Session = Depends(get_db)):
    return dealer_service.recent_dealers(db, auth.company, limit)


@router.get("/{dealer_code}", response_model=DealerOut)
def get_dealer(dealer_code: str, auth: AuthContext = Depends(get_auth), db: Session = Depends(get_db)):
    return dealer_service.dealer_to_out(dealer_service.get_dealer(db, auth.company, dealer_code))


@router.post("/{dealer_code}/messages", response_model=CommunicationOut, status_code=201)
def send_message(
    dealer_code: str,
    subject: str = Form(...),
    message: str = Form(...),
    attachment: UploadFile | None = File(None),
    auth: AuthContext = Depends(get_auth),
    db: Session = Depends(get_db),
):
    incoming = None
    if attachment is not None and attachment.filename:
        limit = get_settings().max_upload_bytes
        content = attachment.file.read(limit + 1)
        if len(content) > limit:
            raise ApiError(413, f"Attachment must be {get_settings().max_upload_mb} MB or smaller.")
        incoming = communication_service.IncomingFile(attachment.filename, attachment.content_type, content)
    return communication_service.send_message(
        db, auth.company, auth.user, dealer_code, subject=subject, message=message, attachment=incoming
    )


@router.post("/{dealer_code}/interactions", response_model=CommunicationOut, status_code=201)
def log_interaction(
    dealer_code: str, payload: InteractionCreate, auth: AuthContext = Depends(get_auth), db: Session = Depends(get_db)
):
    """Record an email opened in the mail client or a phone call started from the portal."""
    return communication_service.log_interaction(
        db, auth.company, auth.user, dealer_code, kind=payload.type, subject=payload.subject
    )
