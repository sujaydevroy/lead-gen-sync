"""Port of frontend/src/lib/salesAnalytics.js. Pure functions over sales record dicts.

Records use the frontend's keys (customerName, country, period, product, amount, currency, ...).
Filtered rows get an extra "value" key: the amount expressed in the reporting currency.
"""

from __future__ import annotations

from typing import Any

from app.services.analytics.fx import convert_amount
from app.services.analytics.jsmath import js_sum

ALL_CURRENCIES = "ALL"


def default_filters() -> dict[str, Any]:
    return {
        "currency": ALL_CURRENCIES,
        "reportingCurrency": "USD",
        "dateFrom": "",
        "dateTo": "",
        "customers": [],
        "products": [],
        "countries": [],
    }


# ---------------------------------------------------------------------------
# Periods
# ---------------------------------------------------------------------------


def add_months(period: str, count: int) -> str:
    y, m = (int(p) for p in period.split("-"))
    index = y * 12 + (m - 1) + count
    return f"{index // 12}-{index % 12 + 1:02d}"


def months_between(start: str, end: str) -> int:
    fy, fm = (int(p) for p in start.split("-"))
    ty, tm = (int(p) for p in end.split("-"))
    return (ty - fy) * 12 + (tm - fm)


# ---------------------------------------------------------------------------
# Options + filtering
# ---------------------------------------------------------------------------


def _unique_sorted(values) -> list[str]:
    return sorted({v for v in values if v}, key=str.casefold)


def get_sales_options(records: list[dict]) -> dict[str, Any]:
    periods = sorted({r["period"] for r in records})
    return {
        "customers": _unique_sorted(r["customerName"] for r in records),
        "products": _unique_sorted(r["product"] for r in records),
        "countries": _unique_sorted(r["country"] for r in records),
        "currencies": _unique_sorted(r["currency"] for r in records),
        "firstPeriod": periods[0] if periods else "",
        "lastPeriod": periods[-1] if periods else "",
    }


def apply_sales_filters(records: list[dict], filters: dict, fx_rates: dict[str, float]) -> dict[str, Any]:
    single = bool(filters.get("currency")) and filters["currency"] != ALL_CURRENCIES
    currency = filters["currency"] if single else filters["reportingCurrency"]
    unknown: list[str] = []
    excluded = 0
    rows: list[dict] = []
    for record in records:
        if single and record["currency"] != filters["currency"]:
            continue
        if filters.get("dateFrom") and record["period"] < filters["dateFrom"]:
            continue
        if filters.get("dateTo") and record["period"] > filters["dateTo"]:
            continue
        if filters.get("customers") and record["customerName"] not in filters["customers"]:
            continue
        if filters.get("products") and record["product"] not in filters["products"]:
            continue
        if filters.get("countries") and record["country"] not in filters["countries"]:
            continue
        value = record["amount"] if single else convert_amount(record["amount"], record["currency"], currency, fx_rates)
        if value is None:
            if record["currency"] not in unknown:
                unknown.append(record["currency"])
            excluded += 1
            continue
        rows.append({**record, "value": value})
    return {"rows": rows, "currency": currency, "converted": not single, "excludedRows": excluded, "unknownCurrencies": unknown}


# ---------------------------------------------------------------------------
# Aggregations
# ---------------------------------------------------------------------------


def aggregate_by_month(rows: list[dict]) -> list[dict]:
    """Continuous monthly series; months inside the range without rows are 0."""
    if not rows:
        return []
    totals: dict[str, float] = {}
    counts: dict[str, int] = {}
    for r in rows:
        totals[r["period"]] = totals.get(r["period"], 0) + r["value"]
        counts[r["period"]] = counts.get(r["period"], 0) + 1
    periods = sorted(totals)
    first = periods[0]
    span = months_between(first, periods[-1])
    series = []
    for i in range(span + 1):
        period = add_months(first, i)
        series.append({"period": period, "value": totals.get(period, 0), "transactions": counts.get(period, 0)})
    return series


def aggregate_by_quarter(monthly: list[dict]) -> list[dict]:
    totals: dict[str, dict] = {}
    for p in monthly:
        y, m = (int(x) for x in p["period"].split("-"))
        key = f"{y}-Q{(m + 2) // 3}"
        entry = totals.setdefault(key, {"quarter": key, "value": 0, "months": 0})
        entry["value"] += p["value"]
        entry["months"] += 1
    return list(totals.values())


def aggregate_by(rows: list[dict], key: str) -> list[dict]:
    totals: dict[str, dict] = {}
    for r in rows:
        entry = totals.setdefault(r[key], {"name": r[key], "value": 0, "transactions": 0})
        entry["value"] += r["value"]
        entry["transactions"] += 1
    grand_total = js_sum(r["value"] for r in rows)
    result = [{**e, "share": (e["value"] / grand_total) * 100 if grand_total > 0 else 0} for e in totals.values()]
    return sorted(result, key=lambda e: -e["value"])


def aggregate_by_product(rows):
    return aggregate_by(rows, "product")


def aggregate_by_dealer(rows):
    return aggregate_by(rows, "customerName")


def aggregate_by_region(rows):
    return aggregate_by(rows, "country")


# ---------------------------------------------------------------------------
# Growth + concentration
# ---------------------------------------------------------------------------


def growth_rate(current: float, previous: float | None) -> float | None:
    if previous is None or previous == 0:
        return None
    return ((current - previous) / abs(previous)) * 100


def calculate_growth(monthly: list[dict]) -> dict[str, Any]:
    n = len(monthly)
    if n < 2:
        return {"mom": None, "yoy": None, "trailing12": None, "latest": monthly[-1] if monthly else None}
    latest, previous = monthly[-1], monthly[-2]
    year_ago = monthly[n - 13] if n >= 13 else None

    def total(items):
        return js_sum(p["value"] for p in items)

    return {
        "latest": latest,
        "previous": previous,
        "yearAgo": year_ago,
        "mom": growth_rate(latest["value"], previous["value"]),
        "yoy": growth_rate(latest["value"], year_ago["value"]) if year_ago else None,
        "trailing12": growth_rate(total(monthly[-12:]), total(monthly[-24:-12])) if n >= 24 else None,
    }


def concentration(ranked: list[dict], top_n: int = 3) -> dict[str, Any] | None:
    if not ranked:
        return None
    top_share = js_sum(e["share"] for e in ranked[:top_n])
    hhi = js_sum(e["share"] * e["share"] for e in ranked)
    level = "High" if hhi >= 2500 else "Moderate" if hhi >= 1500 else "Low"
    return {"topN": min(top_n, len(ranked)), "topShare": top_share, "hhi": hhi, "level": level, "entities": len(ranked)}


def find_decliners(rows: list[dict], monthly: list[dict], key: str) -> dict[str, Any]:
    n = len(monthly)
    window = min(6, n // 2)
    if window < 1:
        return {"window": 0, "items": []}
    recent_start = monthly[n - window]["period"]
    prior_start = monthly[n - 2 * window]["period"]
    recent_end = monthly[n - 1]["period"]
    totals: dict[str, dict] = {}
    for r in rows:
        if r["period"] < prior_start or r["period"] > recent_end:
            continue
        entry = totals.setdefault(r[key], {"name": r[key], "prior": 0, "recent": 0})
        if r["period"] >= recent_start:
            entry["recent"] += r["value"]
        else:
            entry["prior"] += r["value"]
    items = [
        {**e, "change": growth_rate(e["recent"], e["prior"])}
        for e in totals.values()
        if e["prior"] > 0 and e["recent"] < e["prior"]
    ]
    items.sort(key=lambda e: e["change"])
    return {
        "window": window,
        "priorRange": [prior_start, monthly[n - window - 1]["period"]],
        "recentRange": [recent_start, recent_end],
        "items": items,
    }


def calculate_kpis(rows: list[dict], monthly: list[dict], products: list[dict], dealers: list[dict]) -> dict:
    total = js_sum(r["value"] for r in rows)
    return {
        "totalSales": total,
        "transactions": len(rows),
        "averageTransactionValue": total / len(rows) if rows else None,
        "averageMonthlySales": total / len(monthly) if monthly else None,
        "months": len(monthly),
        "topProduct": products[0] if products else None,
        "topDealer": dealers[0] if dealers else None,
        "growth": calculate_growth(monthly),
        "quarterly": aggregate_by_quarter(monthly),
    }


def build_sales_chart_data(rows: list[dict]) -> dict[str, Any]:
    monthly = aggregate_by_month(rows)
    products = aggregate_by_product(rows)
    dealers = aggregate_by_dealer(rows)
    return {
        "monthly": monthly,
        "products": products[:10],
        "productCount": len(products),
        "countries": aggregate_by_region(rows),
        "dealers": dealers[:10],
        "dealerCount": len(dealers),
        "total": js_sum(r["value"] for r in rows),
        "transactions": len(rows),
    }
