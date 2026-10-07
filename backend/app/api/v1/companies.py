from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_auth
from app.core.database import get_db
from app.core.errors import ApiError
from app.schemas.company import CompanyOut, SectorDefinition
from app.services import company_service

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("/me", response_model=CompanyOut)
def my_company(auth: AuthContext = Depends(get_auth)):
    return company_service.company_to_out(auth.company)


@router.get("/me/sector", response_model=SectorDefinition)
def my_sector(auth: AuthContext = Depends(get_auth), db: Session = Depends(get_db)):
    """The company's sector and its sub-sectors (scopes the Sector / Sub-sector dealer filters)."""
    definition = company_service.sector_definition(db, auth.company)
    if definition is None:
        raise ApiError(404, "No sector is configured for your company.")
    return definition
