"""Exchange rates: global defaults (company_id NULL) with per-company overrides."""

from __future__ import annotations

from datetime import date

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models import Company, Currency, ExchangeRate
from app.schemas.sales import ExchangeRatesOut


def effective_rates(db: Session, company: Company, on: date | None = None) -> ExchangeRatesOut:
    """Latest rate per currency on or before `on`; a company override beats the global rate."""
    on = on or date.today()
    rows = db.scalars(
        select(ExchangeRate)
        .where(
            ExchangeRate.is_active,
            ExchangeRate.effective_date <= on,
            or_(ExchangeRate.company_id.is_(None), ExchangeRate.company_id == company.id),
        )
        .order_by(ExchangeRate.effective_date)
    ).all()
    global_rates: dict[str, ExchangeRate] = {}
    company_rates: dict[str, ExchangeRate] = {}
    for row in rows:  # ascending dates: later rows overwrite earlier ones
        (company_rates if row.company_id else global_rates)[row.currency.code] = row
    merged = {**global_rates, **company_rates}
    as_of = max((r.effective_date for r in merged.values()), default=None)
    return ExchangeRatesOut(
        as_of=as_of,
        rates={code: float(r.rate_to_usd) for code, r in sorted(merged.items())},
        overridden=sorted(company_rates),
    )


def update_rates(db: Session, company: Company, rates: dict[str, float]) -> ExchangeRatesOut:
    currencies = {c.code: c for c in db.scalars(select(Currency).where(Currency.code.in_(list(rates))))}
    unknown = sorted(set(rates) - set(currencies))
    if unknown:
        raise ApiError(422, f"Unknown currency code(s): {', '.join(unknown)}.")
    if "USD" in rates and rates["USD"] != 1:
        raise ApiError(422, "USD is the base currency; its rate must be 1.")
    today = date.today()
    for code, rate in rates.items():
        row = db.scalar(
            select(ExchangeRate).where(
                ExchangeRate.company_id == company.id,
                ExchangeRate.currency_id == currencies[code].id,
                ExchangeRate.effective_date == today,
            )
        )
        if row is None:
            row = ExchangeRate(company_id=company.id, currency_id=currencies[code].id, effective_date=today)
            db.add(row)
        row.rate_to_usd = rate
        row.is_active = True
        row.source = "Company override"
    db.commit()
    return effective_rates(db, company)


def reset_overrides(db: Session, company: Company) -> ExchangeRatesOut:
    db.execute(update(ExchangeRate).where(ExchangeRate.company_id == company.id).values(is_active=False))
    db.commit()
    return effective_rates(db, company)
