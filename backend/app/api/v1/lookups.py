from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_auth
from app.core.database import get_db
from app.models import CommunicationType, Country, Dealer, DealerStatus, DealerType, Region
from app.schemas.common import NamedCount

router = APIRouter(prefix="/lookups", tags=["lookups"])


@router.get("/countries", response_model=list[NamedCount])
def countries(auth: AuthContext = Depends(get_auth), db: Session = Depends(get_db)):
    """Countries that have dealers, with dealer counts (dealerService.getCountries)."""
    rows = db.execute(
        select(Country.name, func.count(Dealer.id))
        .join(Dealer, Dealer.country_id == Country.id)
        .where(Dealer.company_id == auth.company.id, Dealer.is_active)
        .group_by(Country.name)
        .order_by(Country.name)
    )
    return [NamedCount(name=name, count=count) for name, count in rows]


@router.get("/regions", response_model=list[NamedCount])
def regions(country: list[str] = Query(default=[]), auth: AuthContext = Depends(get_auth), db: Session = Depends(get_db)):
    """Regions with dealer counts, optionally limited to one or more countries (dealerService.getRegions)."""
    stmt = (
        select(Region.name, func.count(Dealer.id))
        .join(Dealer, Dealer.region_id == Region.id)
        .where(Dealer.company_id == auth.company.id, Dealer.is_active)
        .group_by(Region.name, Region.sort_order)
        .order_by(Region.sort_order)
    )
    if country:
        stmt = stmt.where(Dealer.country_id.in_(select(Country.id).where(Country.name.in_(country))))
    return [NamedCount(name=name, count=count) for name, count in db.execute(stmt)]


def _names(db: Session, model) -> list[str]:
    return list(db.scalars(select(model.name).where(model.is_active).order_by(model.id)))


@router.get("/dealer-types", response_model=list[str])
def dealer_types(_: AuthContext = Depends(get_auth), db: Session = Depends(get_db)):
    return _names(db, DealerType)


@router.get("/dealer-statuses", response_model=list[str])
def dealer_statuses(_: AuthContext = Depends(get_auth), db: Session = Depends(get_db)):
    return _names(db, DealerStatus)


@router.get("/communication-types", response_model=list[str])
def communication_types(_: AuthContext = Depends(get_auth), db: Session = Depends(get_db)):
    return _names(db, CommunicationType)
