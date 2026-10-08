from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_auth, require_role
from app.core.database import get_db
from app.core.errors import ApiError
from app.core.roles import COMPANY_ADMIN
from app.schemas.admin import CompanyFields
from app.schemas.company import CompanyOptions, CompanyOut, SectorDefinition
from app.services import admin_service, company_service

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("/me", response_model=CompanyOut)
def my_company(auth: AuthContext = Depends(get_auth)):
    return company_service.company_to_out(auth.company)


@router.put("/me", response_model=CompanyOut)
def update_my_company(
    payload: CompanyFields, auth: AuthContext = Depends(require_role(COMPANY_ADMIN)), db: Session = Depends(get_db)
):
    """Edit the signed-in user's own company profile (PUT replaces the whole profile; Company Administrators only)."""
    return admin_service.update_own_company(db, auth.company, payload)


@router.get("/me/options", response_model=CompanyOptions)
def company_options(_: AuthContext = Depends(get_auth), db: Session = Depends(get_db)):
    """Sectors, countries and regions the company profile form can choose from."""
    return admin_service.company_options(db)


@router.get("/me/sector", response_model=SectorDefinition)
def my_sector(auth: AuthContext = Depends(get_auth), db: Session = Depends(get_db)):
    """The company's sector and its sub-sectors (scopes the Sector / Sub-sector dealer filters)."""
    definition = company_service.sector_definition(db, auth.company)
    if definition is None:
        raise ApiError(404, "No sector is configured for your company.")
    return definition
