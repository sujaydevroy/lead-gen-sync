from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, SubSector
from app.schemas.company import CompanyAddress, CompanyOut, SectorDefinition


def company_to_out(company: Company) -> CompanyOut:
    return CompanyOut(
        id=company.company_code,
        name=company.name,
        logo_text=company.logo_text,
        logo_url=company.logo_url,
        industry=company.industry,
        sector=company.sector.name if company.sector else None,
        website=company.website,
        email=company.email,
        phone=company.phone,
        address=CompanyAddress(
            line1=company.address_line1,
            city=company.city,
            state=company.state,
            postal_code=company.postal_code,
            country=company.country.name if company.country else None,
            region=company.region.name if company.region else None,
        ),
        registration_number=company.registration_number,
        tax_id=company.tax_id,
        employees=company.employee_count,
        founded=str(company.founded_year) if company.founded_year else None,
    )


def company_sub_sectors(db: Session, company: Company) -> list[SubSector]:
    if company.sector_id is None:
        return []
    return list(
        db.scalars(
            select(SubSector)
            .where(SubSector.sector_id == company.sector_id, SubSector.is_active)
            .order_by(SubSector.sort_order, SubSector.name)
        )
    )


def sector_definition(db: Session, company: Company) -> SectorDefinition | None:
    if company.sector is None:
        return None
    return SectorDefinition(sector=company.sector.name, sub_sectors=[s.name for s in company_sub_sectors(db, company)])
