"""System administration (role "System Administrator" only): companies, their users (read-only), dealer uploads."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, require_role
from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import ApiError
from app.core.roles import SYSTEM_ADMIN
from app.schemas.admin import (
    AdminCompanyOut,
    AdminLookups,
    AdminUserUpdate,
    CompanyCreate,
    CompanyFields,
    DealerDirectoryStats,
    DealerUploadOut,
    ManagedUserOut,
    PasswordSet,
)
from app.services import admin_service, dealer_import_service

router = APIRouter(prefix="/admin", tags=["admin"])
sysadmin = require_role(SYSTEM_ADMIN)


@router.get("/lookups", response_model=AdminLookups)
def lookups(_: AuthContext = Depends(sysadmin), db: Session = Depends(get_db)):
    """Countries, regions, sectors, dealer types / statuses and currencies for the admin forms."""
    return admin_service.lookups(db)


@router.get("/companies", response_model=list[AdminCompanyOut])
def list_companies(
    search: str = "",
    include_inactive: bool = Query(default=True, alias="includeInactive"),
    _: AuthContext = Depends(sysadmin),
    db: Session = Depends(get_db),
):
    return admin_service.list_companies(db, search=search, include_inactive=include_inactive)


@router.post("/companies", response_model=AdminCompanyOut, status_code=201)
def create_company(payload: CompanyCreate, _: AuthContext = Depends(sysadmin), db: Session = Depends(get_db)):
    """Create a company together with its first Company Administrator (who then manages the company's users)."""
    return admin_service.create_company(db, payload)


@router.get("/companies/{company_code}", response_model=AdminCompanyOut)
def get_company(company_code: str, _: AuthContext = Depends(sysadmin), db: Session = Depends(get_db)):
    return admin_service.company_detail(db, company_code)


@router.put("/companies/{company_code}", response_model=AdminCompanyOut)
def update_company(company_code: str, payload: CompanyFields, _: AuthContext = Depends(sysadmin), db: Session = Depends(get_db)):
    return admin_service.update_company(db, company_code, payload)


@router.delete("/companies/{company_code}", response_model=AdminCompanyOut)
def deactivate_company(company_code: str, _: AuthContext = Depends(sysadmin), db: Session = Depends(get_db)):
    """Soft delete: the company's users can no longer sign in. Restore with POST .../activate."""
    return admin_service.set_company_active(db, company_code, False)


@router.post("/companies/{company_code}/activate", response_model=AdminCompanyOut)
def activate_company(company_code: str, _: AuthContext = Depends(sysadmin), db: Session = Depends(get_db)):
    return admin_service.set_company_active(db, company_code, True)


@router.get("/companies/{company_code}/users", response_model=list[ManagedUserOut])
def company_users(company_code: str, _: AuthContext = Depends(sysadmin), db: Session = Depends(get_db)):
    return admin_service.company_users(db, company_code)


@router.patch("/companies/{company_code}/users/{user_code}", response_model=ManagedUserOut)
def update_company_user(
    company_code: str, user_code: str, payload: AdminUserUpdate, _: AuthContext = Depends(sysadmin), db: Session = Depends(get_db)
):
    """Edit a user's name, email, job title, phone or role (only the fields sent change)."""
    return admin_service.update_company_user(db, company_code, user_code, payload)


@router.post("/companies/{company_code}/users/{user_code}/unlock", response_model=ManagedUserOut)
def unlock_company_user(company_code: str, user_code: str, _: AuthContext = Depends(sysadmin), db: Session = Depends(get_db)):
    return admin_service.unlock_company_user(db, company_code, user_code)


@router.post("/companies/{company_code}/users/{user_code}/password", response_model=ManagedUserOut)
def set_company_user_password(
    company_code: str, user_code: str, payload: PasswordSet, _: AuthContext = Depends(sysadmin), db: Session = Depends(get_db)
):
    """Set a temporary password for the user (they are signed out everywhere)."""
    return admin_service.set_company_user_password(db, company_code, user_code, payload.password)


@router.get("/dealer-directory", response_model=DealerDirectoryStats)
def dealer_directory(_: AuthContext = Depends(sysadmin), db: Session = Depends(get_db)):
    """Size of the dealer directory (dcp.dealers: active dealers, shared by all client companies)."""
    return DealerDirectoryStats(dealer_count=dealer_import_service.directory_dealer_count(db))


@router.post("/dealer-uploads", response_model=DealerUploadOut, status_code=201)
def upload_dealers(
    file: UploadFile = File(...),
    auth: AuthContext = Depends(sysadmin),
    db: Session = Depends(get_db),
):
    """Upload an .xlsx / .xls / .csv / .json dealer file into the dealer directory.

    Rows go straight into dcp.dealers (existing Dealer IDs are updated, others inserted) and its product tables.
    Dealers belong to no company; clients are matched to them through the products they deal in.
    The response summarises the outcome and lists the rows that were skipped.
    """
    settings = get_settings()
    content = file.file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise ApiError(413, f"The file is larger than {settings.max_upload_mb} MB.")
    return dealer_import_service.import_dealers(db, content=content, file_name=file.filename or "dealers.xlsx")


@router.get("/dealer-uploads/template")
def dealer_upload_template(_: AuthContext = Depends(sysadmin), db: Session = Depends(get_db)):
    return Response(
        dealer_import_service.template_workbook(db),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="dealer_upload_template.xlsx"'},
    )
