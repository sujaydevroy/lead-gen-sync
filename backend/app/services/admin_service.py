"""System administration: every customer company (create, edit, activate / deactivate) and its users (read-only).

The users of a company are managed by its own Company Administrator (see company_user_service).
"""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import ApiError, not_found
from app.core.roles import COMPANY_ADMIN
from app.core.security import hash_password
from app.models import Company, Country, Currency, Dealer, DealerStatus, DealerType, Region, Role, Sector, User
from app.schemas.admin import AdminCompanyOut, AdminLookups, CompanyCreate, CompanyFields, ManagedUserOut
from app.services import auth_service
from app.services.codes import next_code
from app.services.company_service import company_to_out
from app.services.company_user_service import user_to_managed_out


def lookup_id(db: Session, model, name: str | None, label: str) -> int | None:
    """Id of the active lookup row with this name (case-insensitive); 422 when it doesn't exist."""
    if name is None:
        return None
    row_id = db.scalar(select(model.id).where(func.lower(model.name) == name.strip().lower(), model.is_active))
    if row_id is None:
        raise ApiError(422, f"Unknown {label} '{name}'.")
    return row_id


def _counts(db: Session, model, company_ids: list[int]) -> dict[int, int]:
    if not company_ids:
        return {}
    rows = db.execute(
        select(model.company_id, func.count(model.id))
        .where(model.company_id.in_(company_ids), model.is_active)
        .group_by(model.company_id)
    )
    return dict(rows.all())


def _to_out(company: Company, users: int, dealers: int) -> AdminCompanyOut:
    return AdminCompanyOut(
        **company_to_out(company).model_dump(),
        is_active=company.is_active,
        user_count=users,
        dealer_count=dealers,
        created_on=company.created_on,
    )


def _one_out(db: Session, company: Company) -> AdminCompanyOut:
    ids = [company.id]
    return _to_out(company, _counts(db, User, ids).get(company.id, 0), _counts(db, Dealer, ids).get(company.id, 0))


def list_companies(db: Session, *, search: str = "", include_inactive: bool = True) -> list[AdminCompanyOut]:
    stmt = select(Company).where(Company.is_platform.is_(False)).order_by(func.lower(Company.name))
    if search.strip():
        term = f"%{search.strip()}%"
        stmt = stmt.where(or_(Company.name.ilike(term), Company.company_code.ilike(term)))
    if not include_inactive:
        stmt = stmt.where(Company.is_active)
    companies = list(db.scalars(stmt))
    ids = [c.id for c in companies]
    users, dealers = _counts(db, User, ids), _counts(db, Dealer, ids)
    return [_to_out(c, users.get(c.id, 0), dealers.get(c.id, 0)) for c in companies]


def get_company(db: Session, company_code: str) -> Company:
    """A customer company by code (inactive ones included; the platform company is never returned)."""
    company = db.scalar(select(Company).where(Company.company_code == company_code, Company.is_platform.is_(False)))
    if company is None:
        raise not_found("Company")
    return company


def company_detail(db: Session, company_code: str) -> AdminCompanyOut:
    return _one_out(db, get_company(db, company_code))


def _initials(name: str) -> str:
    words = [w for w in name.replace("&", " ").split() if w[:1].isalnum()]
    return "".join(w[0] for w in words[:3]).upper() or name[:2].upper()


def _apply_fields(db: Session, company: Company, payload: CompanyFields) -> None:
    company.name = payload.name
    company.logo_text = payload.logo_text or _initials(payload.name)
    company.industry = payload.industry
    company.sector_id = lookup_id(db, Sector, payload.sector, "sector")
    company.website = payload.website
    company.email = str(payload.email) if payload.email else None
    company.phone = payload.phone
    company.address_line1 = payload.address_line1
    company.city = payload.city
    company.state = payload.state
    company.postal_code = payload.postal_code
    company.country_id = lookup_id(db, Country, payload.country, "country")
    company.region_id = lookup_id(db, Region, payload.region, "region")
    company.registration_number = payload.registration_number
    company.tax_id = payload.tax_id
    company.employee_count = payload.employees
    company.founded_year = payload.founded


def create_company(db: Session, payload: CompanyCreate) -> AdminCompanyOut:
    admin = payload.admin
    if auth_service.find_user_by_email(db, str(admin.email)) is not None:
        raise ApiError(409, f"A user with the email {admin.email} already exists.")
    auth_service.validate_new_password(admin.password)
    role_id = lookup_id(db, Role, COMPANY_ADMIN, "role")

    company = Company(company_code=next_code(db, Company.company_code, "CMP", start=10001), is_platform=False)
    _apply_fields(db, company, payload)
    db.add(company)
    db.flush()
    db.add(
        User(
            company_id=company.id,
            role_id=role_id,
            user_code=next_code(db, User.user_code, "USR", start=2001),
            full_name=admin.name,
            email=str(admin.email),
            job_title=admin.job_title,
            phone=admin.phone,
            country_id=company.country_id,
            region_id=company.region_id,
            password_hash=hash_password(admin.password),
        )
    )
    db.commit()
    db.refresh(company)
    return _one_out(db, company)


def update_company(db: Session, company_code: str, payload: CompanyFields) -> AdminCompanyOut:
    company = get_company(db, company_code)
    _apply_fields(db, company, payload)
    db.commit()
    db.refresh(company)
    return _one_out(db, company)


def set_company_active(db: Session, company_code: str, active: bool) -> AdminCompanyOut:
    """Soft delete / restore. The users of an inactive company can no longer sign in or use the API."""
    company = get_company(db, company_code)
    company.is_active = active
    db.commit()
    db.refresh(company)
    return _one_out(db, company)


def company_users(db: Session, company_code: str) -> list[ManagedUserOut]:
    company = get_company(db, company_code)
    users = db.scalars(select(User).where(User.company_id == company.id).order_by(func.lower(User.full_name)))
    return [user_to_managed_out(u) for u in users]


def _names(db: Session, model, order_by) -> list[str]:
    return list(db.scalars(select(model.name).where(model.is_active).order_by(order_by)))


def lookups(db: Session) -> AdminLookups:
    return AdminLookups(
        countries=_names(db, Country, Country.name),
        regions=_names(db, Region, Region.sort_order),
        sectors=_names(db, Sector, Sector.name),
        dealer_types=_names(db, DealerType, DealerType.id),
        dealer_statuses=_names(db, DealerStatus, DealerStatus.id),
        currencies=list(db.scalars(select(Currency.code).where(Currency.is_active).order_by(Currency.code))),
    )
