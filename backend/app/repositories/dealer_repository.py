"""SQL for the dealer list: search, filters, facet counts and pagination.

Same semantics as frontend/src/lib/dealerFiltering.js:
  * filter groups are AND-ed, values inside a group are OR-ed;
  * each facet's counts apply every OTHER active filter group plus the search;
  * sub-sector matching uses dealer_products -> product_sub_sectors (no regex at query time).
"""

from __future__ import annotations

from sqlalchemy import ColumnElement, and_, distinct, exists, func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    Country,
    Dealer,
    DealerProduct,
    DealerStatus,
    DealerType,
    ProductSubSector,
    Region,
    Sector,
    SubSector,
)
from app.schemas.dealer import DealerFilters

FILTER_GROUPS = ("countries", "regions", "statuses", "types", "sectors", "sub_sectors")


def escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def search_condition(search: str) -> ColumnElement[bool] | None:
    term = (search or "").strip()
    if not term:
        return None
    pattern = f"%{escape_like(term)}%"
    columns = (Dealer.dealer_name, Dealer.dealer_code, Dealer.legal_name, Dealer.city, Dealer.contact_person, Dealer.email)
    return or_(*(col.ilike(pattern, escape="\\") for col in columns))


def _sub_sector_exists(sub_sector_ids: list[int]) -> ColumnElement[bool]:
    return exists(
        select(DealerProduct.id)
        .join(ProductSubSector, and_(ProductSubSector.product_id == DealerProduct.product_id, ProductSubSector.is_active))
        .where(
            DealerProduct.dealer_id == Dealer.id,
            DealerProduct.is_active,
            ProductSubSector.sub_sector_id.in_(sub_sector_ids),
        )
    )


def _group_condition(group: str, values: list[str], sub_sector_ids: list[int]) -> ColumnElement[bool] | None:
    if group == "sub_sectors":
        if not values:
            return None
        return _sub_sector_exists(sub_sector_ids) if sub_sector_ids else Dealer.id.is_(None)  # unknown names -> no match
    if not values:
        return None
    lookup = {
        "countries": (Dealer.country_id, Country),
        "regions": (Dealer.region_id, Region),
        "statuses": (Dealer.dealer_status_id, DealerStatus),
        "types": (Dealer.dealer_type_id, DealerType),
        "sectors": (Dealer.sector_id, Sector),
    }[group]
    column, model = lookup
    return column.in_(select(model.id).where(model.name.in_(values)))


class DealerQuery:
    """Builds WHERE clauses for one request (company scope + search + filter groups)."""

    def __init__(self, company_id: int, search: str, filters: DealerFilters, sub_sector_ids: list[int]):
        self.base = [Dealer.company_id == company_id, Dealer.is_active]
        searched = search_condition(search)
        if searched is not None:
            self.base.append(searched)
        self.groups: dict[str, ColumnElement[bool]] = {}
        for group in FILTER_GROUPS:
            condition = _group_condition(group, getattr(filters, group), sub_sector_ids)
            if condition is not None:
                self.groups[group] = condition

    def where(self, skip: str | None = None) -> list[ColumnElement[bool]]:
        return [*self.base, *(cond for group, cond in self.groups.items() if group != skip)]


def resolve_sub_sector_ids(db: Session, sector_id: int | None, names: list[str]) -> list[int]:
    if not names or sector_id is None:
        return []
    return list(db.scalars(select(SubSector.id).where(SubSector.sector_id == sector_id, SubSector.name.in_(names))))


def count(db: Session, conditions: list[ColumnElement[bool]]) -> int:
    return db.scalar(select(func.count(Dealer.id)).where(*conditions)) or 0


def page(db: Session, conditions: list[ColumnElement[bool]], offset: int, limit: int) -> list[Dealer]:
    stmt = (
        select(Dealer).where(*conditions).order_by(func.lower(Dealer.dealer_name), Dealer.dealer_code).offset(offset).limit(limit)
    )
    return list(db.scalars(stmt).unique())


def counts_by(db: Session, name_column, join_model, join_on, conditions) -> dict[str, int]:
    stmt = (
        select(name_column, func.count(Dealer.id))
        .select_from(Dealer)
        .join(join_model, join_on)
        .where(*conditions)
        .group_by(name_column)
    )
    return {name: total for name, total in db.execute(stmt)}


def sub_sector_counts(db: Session, conditions, sub_sector_ids: list[int]) -> dict[int, int]:
    if not sub_sector_ids:
        return {}
    stmt = (
        select(ProductSubSector.sub_sector_id, func.count(distinct(Dealer.id)))
        .select_from(Dealer)
        .join(DealerProduct, and_(DealerProduct.dealer_id == Dealer.id, DealerProduct.is_active))
        .join(ProductSubSector, and_(ProductSubSector.product_id == DealerProduct.product_id, ProductSubSector.is_active))
        .where(*conditions, ProductSubSector.sub_sector_id.in_(sub_sector_ids))
        .group_by(ProductSubSector.sub_sector_id)
    )
    return {sub_id: total for sub_id, total in db.execute(stmt)}


def country_region_pairs(db: Session, company_id: int) -> list[tuple[str, str, int]]:
    stmt = (
        select(Country.name, Region.name, Region.sort_order)
        .select_from(Dealer)
        .join(Country, Country.id == Dealer.country_id)
        .join(Region, Region.id == Dealer.region_id)
        .where(Dealer.company_id == company_id, Dealer.is_active)
        .distinct()
    )
    return [tuple(row) for row in db.execute(stmt)]


def company_countries(db: Session, company_id: int) -> list[str]:
    stmt = (
        select(Country.name)
        .select_from(Dealer)
        .join(Country, Country.id == Dealer.country_id)
        .where(Dealer.company_id == company_id, Dealer.is_active)
        .distinct()
        .order_by(Country.name)
    )
    return list(db.scalars(stmt))


def get_by_code(db: Session, company_id: int, dealer_code: str) -> Dealer | None:
    return db.scalar(
        select(Dealer).where(
            Dealer.company_id == company_id,
            func.lower(Dealer.dealer_code) == dealer_code.strip().lower(),
            Dealer.is_active,
        )
    )


def recent(db: Session, company_id: int, limit: int) -> list[Dealer]:
    stmt = (
        select(Dealer)
        .where(Dealer.company_id == company_id, Dealer.is_active)
        .order_by(Dealer.created_on.desc(), Dealer.id.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt).unique())


def stats(db: Session, company_id: int) -> dict[str, int]:
    scope = [Dealer.company_id == company_id, Dealer.is_active]
    active = (
        db.scalar(
            select(func.count(Dealer.id))
            .join(DealerStatus, DealerStatus.id == Dealer.dealer_status_id)
            .where(*scope, DealerStatus.name == "Active")
        )
        or 0
    )
    return {
        "total_dealers": count(db, scope),
        "active_dealers": active,
        "countries": db.scalar(select(func.count(distinct(Dealer.country_id))).where(*scope)) or 0,
        "regions": db.scalar(
            select(func.count()).select_from(select(Dealer.country_id, Dealer.region_id).where(*scope).distinct().subquery())
        )
        or 0,
    }
