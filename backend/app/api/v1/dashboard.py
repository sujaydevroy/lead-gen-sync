from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_auth
from app.core.database import get_db
from app.schemas.common import CamelModel
from app.schemas.communication import CommunicationStats
from app.schemas.dealer import DealerStats
from app.services import communication_service, dealer_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class DashboardStats(CamelModel):
    dealers: DealerStats
    communications: CommunicationStats


@router.get("/stats", response_model=DashboardStats)
def dashboard_stats(auth: AuthContext = Depends(get_auth), db: Session = Depends(get_db)):
    return DashboardStats(
        dealers=dealer_service.dealer_stats(db, auth.company),
        communications=communication_service.communication_stats(db, auth.company),
    )
