from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_auth
from app.core.database import get_db
from app.schemas.common import Page
from app.schemas.communication import CommunicationOut, CommunicationStats
from app.services import communication_service

router = APIRouter(prefix="/communications", tags=["communications"])


@router.get("", response_model=Page[CommunicationOut])
def list_communications(
    dealer_id: str | None = Query(None, alias="dealerId", max_length=30),
    types: list[Literal["Email", "Message", "Call", "Meeting"]] = Query(default=[]),
    direction: Literal["inbound", "outbound"] | None = None,
    search: str = Query("", max_length=200),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, alias="pageSize", ge=1, le=200),
    auth: AuthContext = Depends(get_auth),
    db: Session = Depends(get_db),
):
    return communication_service.list_communications(
        db,
        auth.company,
        dealer_code=dealer_id,
        types=list(types),
        direction=direction,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get("/recent", response_model=list[CommunicationOut])
def recent(limit: int = Query(6, ge=1, le=50), auth: AuthContext = Depends(get_auth), db: Session = Depends(get_db)):
    return communication_service.recent_communications(db, auth.company, limit)


@router.get("/stats", response_model=CommunicationStats)
def stats(auth: AuthContext = Depends(get_auth), db: Session = Depends(get_db)):
    return communication_service.communication_stats(db, auth.company)


@router.get("/{communication_id}/attachments/{attachment_id}")
def download_attachment(
    communication_id: int, attachment_id: int, auth: AuthContext = Depends(get_auth), db: Session = Depends(get_db)
):
    attachment, content = communication_service.get_attachment(db, auth.company, communication_id, attachment_id)
    return Response(
        content,
        media_type=attachment.content_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{attachment.file_name}"',
            "X-Content-Type-Options": "nosniff",
        },
    )
