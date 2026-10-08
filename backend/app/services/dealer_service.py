"""Dealer use cases: the paginated list with facets, details, search, recent and stats."""

from __future__ import annotations

import math
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import not_found
from app.models import Company, Country, Dealer, DealerStatus, DealerType, Region, Sector
from app.repositories import dealer_repository as repo
from app.schemas.dealer import DealerFacets, DealerFilters, DealerListResponse, DealerOut, DealerStats, FacetOption
from app.services.company_service import company_sub_sectors

NOT_AVAILABLE = "Not Available"
PAGE_SIZES = (10, 20, 50)


def _text(value) -> str:
    if value is None:
        return NOT_AVAILABLE
    value = str(value).strip()
    return value or NOT_AVAILABLE


def _amount(value: Decimal | None) -> str:
    if value is None:
        return NOT_AVAILABLE
    return str(int(value)) if value == value.to_integral_value() else format(value.normalize(), "f")


def dealer_to_out(dealer: Dealer) -> DealerOut:
    return DealerOut(
        dealer_id=dealer.dealer_code,
        dealer_name=dealer.dealer_name,
        company_name=_text(dealer.legal_name),
        dealer_type=dealer.dealer_type.name,
        status=dealer.status.name,
        contact_person=_text(dealer.contact_person),
        region=dealer.region.name if dealer.region else NOT_AVAILABLE,
        registration_no=_text(dealer.registration_no),
        full_address=_text(dealer.full_address),
        city=_text(dealer.city),
        state=_text(dealer.state),
        postal_code=_text(dealer.postal_code),
        email=_text(dealer.email),
        phone=_text(dealer.phone),
        website=_text(dealer.website),
        country=dealer.country.name,
        sector=dealer.sector.name if dealer.sector else NOT_AVAILABLE,
        product=[link.product.name for link in dealer.product_links],
        last_transaction_date=dealer.last_transaction_date.isoformat() if dealer.last_transaction_date else NOT_AVAILABLE,
        last_transaction_amount=_amount(dealer.last_transaction_amount),
        currency=dealer.last_transaction_currency.code if dealer.last_transaction_currency else NOT_AVAILABLE,
        source_url=_text(dealer.source_url),
        verification_date=dealer.verification_date.isoformat() if dealer.verification_date else NOT_AVAILABLE,
        created_at=dealer.created_on.isoformat(),
        is_demo=dealer.is_demo,
    )


def list_dealers(
    db: Session, company: Company, *, search: str, filters: DealerFilters, page: int, page_size: int
) -> DealerListResponse:
    page_size = page_size if page_size in PAGE_SIZES else 20
    sub_sectors = company_sub_sectors(db, company)
    sub_sector_ids = repo.resolve_sub_sector_ids(db, company.sector_id, filters.sub_sectors)
    scope = repo.visible_scope(company)
    query = repo.DealerQuery(scope, search, filters, sub_sector_ids)

    total = repo.count(db, query.where())
    total_pages = max(1, math.ceil(total / page_size))
    page = min(max(1, page), total_pages)
    items = repo.page(db, query.where(), (page - 1) * page_size, page_size)

    return DealerListResponse(
        items=[dealer_to_out(d) for d in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        facets=_facets(db, company, scope, query, filters, sub_sectors),
        total_dealers=repo.count(db, scope),
    )


def _facets(db: Session, company: Company, scope, query: repo.DealerQuery, filters: DealerFilters, sub_sectors) -> DealerFacets:
    regions_by_country: dict[str, list[tuple[int, str]]] = {}
    for country, region, sort_order in repo.country_region_pairs(db, scope):
        regions_by_country.setdefault(country, []).append((sort_order, region))
    ordered_regions = {c: [r for _, r in sorted(v)] for c, v in sorted(regions_by_country.items())}
    countries = repo.dealer_countries(db, scope)

    country_counts = repo.counts_by(db, Country.name, Country, Country.id == Dealer.country_id, query.where("countries"))
    region_counts = repo.counts_by(db, Region.name, Region, Region.id == Dealer.region_id, query.where("regions"))
    status_counts = repo.counts_by(
        db, DealerStatus.name, DealerStatus, DealerStatus.id == Dealer.dealer_status_id, query.where("statuses")
    )
    type_counts = repo.counts_by(db, DealerType.name, DealerType, DealerType.id == Dealer.dealer_type_id, query.where("types"))
    sector_counts = repo.counts_by(db, Sector.name, Sector, Sector.id == Dealer.sector_id, query.where("sectors"))
    sub_counts = repo.sub_sector_counts(db, query.where("sub_sectors"), [s.id for s in sub_sectors])

    # Regions available for the selected countries (all regions when none selected).
    region_pool = (
        [(o, r) for c, o_r in regions_by_country.items() if c in filters.countries for o, r in o_r]
        if filters.countries
        else [(o, r) for o_r in regions_by_country.values() for o, r in o_r]
    )
    available_regions = [r for _, r in sorted(set(region_pool))]

    statuses = list(db.scalars(select(DealerStatus.name).where(DealerStatus.is_active).order_by(DealerStatus.id)))
    types = list(db.scalars(select(DealerType.name).where(DealerType.is_active).order_by(DealerType.id)))

    return DealerFacets(
        regions_by_country=ordered_regions,
        countries=[FacetOption(value=c, count=country_counts.get(c, 0)) for c in countries],
        regions=[FacetOption(value=r, count=region_counts.get(r, 0)) for r in available_regions],
        statuses=[FacetOption(value=s, count=status_counts.get(s, 0)) for s in statuses],
        types=[FacetOption(value=t, count=type_counts.get(t, 0)) for t in types],
        sectors=(
            [FacetOption(value=company.sector.name, count=sector_counts.get(company.sector.name, 0))] if company.sector else []
        ),
        sub_sectors=[FacetOption(value=s.name, count=sub_counts.get(s.id, 0)) for s in sub_sectors],
    )


def get_dealer(db: Session, company: Company, dealer_code: str) -> Dealer:
    dealer = repo.get_by_code(db, repo.visible_scope(company), dealer_code)
    if dealer is None:
        raise not_found(f"Dealer {dealer_code}")
    return dealer


def search_dealers(db: Session, company: Company, term: str, limit: int) -> list[DealerOut]:
    query = repo.DealerQuery(repo.visible_scope(company), term, DealerFilters(), [])
    return [dealer_to_out(d) for d in repo.page(db, query.where(), 0, limit)]


def recent_dealers(db: Session, company: Company, limit: int) -> list[DealerOut]:
    return [dealer_to_out(d) for d in repo.recent(db, repo.visible_scope(company), limit)]


def dealer_stats(db: Session, company: Company) -> DealerStats:
    return DealerStats(**repo.stats(db, repo.visible_scope(company)))
