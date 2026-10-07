"""The Python ports must return what the frontend's JavaScript returns for the same input."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from app.services.analytics.sales_analytics import (
    aggregate_by_month,
    aggregate_by_product,
    apply_sales_filters,
    calculate_growth,
    default_filters,
    find_decliners,
)
from app.services.analytics.sales_forecast import create_normal_sampler, forecast_growth, generate_forecast
from app.services.analytics.sales_parsing import parse_sales_rows, read_xlsx

SAMPLE = Path(__file__).resolve().parents[3] / "sample_sales.xlsx"
# Indicative defaults from src/lib/fx.js
RATES = {"USD": 1, "EUR": 1.08, "GBP": 1.27, "INR": 0.012, "AED": 0.2723, "SGD": 0.74, "AUD": 0.66, "CAD": 0.73, "JPY": 0.0067}


@pytest.fixture(scope="module")
def records():
    return parse_sales_rows(read_xlsx(SAMPLE.read_bytes(), max_rows=50_000)).records


def monthly_for(records, **filters):
    return aggregate_by_month(apply_sales_filters(records, {**default_filters(), **filters}, RATES)["rows"])


def test_prng_matches_javascript_sequence():
    # Output of the JS createNormalSampler for the same seed (node, src/lib/salesForecast.js).
    expected = [
        -0.5407329117391175,
        -0.6182381921452209,
        -0.7671970816069651,
        0.04609994997549564,
        0.4863193371550792,
        -1.2995639969892803,
    ]
    normal = create_normal_sampler("2025-01:742428|2025-02:130118.4|ü€😀")
    actual = [normal() for _ in expected]
    assert actual == pytest.approx(expected, rel=1e-12, abs=1e-15)


def test_monthly_series_and_total(records):
    monthly = monthly_for(records)
    assert len(monthly) == 21
    assert monthly[0]["period"] == "2025-01" and monthly[-1]["period"] == "2026-09"
    assert round(sum(p["value"] for p in monthly)) == 5_159_935


def test_forecast_all_currencies_matches_frontend(records):
    monthly = monthly_for(records)
    forecast = generate_forecast(monthly)
    assert forecast["status"] == "ok"
    assert forecast["method"] == "ses" and forecast["params"] == {"alpha": 0.4}
    totals = forecast["scenarioTotals"]
    assert round(totals["base"]) == 1_663_490
    assert round(totals["conservative"]) == 485_974
    assert round(totals["optimistic"]) == 4_340_990
    assert round(forecast_growth(monthly, totals["base"])["growth"], 1) == -6.2
    assert all(p["lower"] <= p["forecast"] <= p["upper"] for p in forecast["points"])
    assert len(forecast["points"]) == 12 and forecast["points"][0]["period"] == "2026-10"


def test_forecast_usd_only_matches_frontend(records):
    forecast = generate_forecast(monthly_for(records, currency="USD"))
    assert forecast["params"] == {"alpha": 0.45}
    assert {k: round(v) for k, v in forecast["scenarioTotals"].items()} == {
        "conservative": 936_599,
        "base": 2_413_842,
        "optimistic": 4_329_728,
    }


def test_sparse_series_is_insufficient(records):
    forecast = generate_forecast(monthly_for(records, currency="EUR"))
    assert forecast["status"] == "insufficient"
    assert "only 4 of 13 months" in forecast["reason"]


def test_short_history_uses_linear_trend_and_two_months_is_insufficient():
    short = [{"period": f"2026-0{i}", "value": v} for i, v in enumerate([100, 120, 130, 150], start=1)]
    forecast = generate_forecast(short)
    assert forecast["method"] == "linear"
    assert round(forecast["points"][0]["forecast"]) == 165
    assert generate_forecast(short[:2])["status"] == "insufficient"


def test_seasonal_model_for_long_history():
    series = [
        {"period": f"{2023 + i // 12}-{i % 12 + 1:02d}", "value": 1000 + 300 * math.sin(i / 12 * 2 * math.pi) + 10 * i}
        for i in range(30)
    ]
    forecast = generate_forecast(series)
    assert forecast["method"] == "holt-winters"
    assert (
        forecast["scenarioTotals"]["conservative"]
        <= forecast["scenarioTotals"]["base"]
        <= forecast["scenarioTotals"]["optimistic"]
    )


def test_growth_decliners_and_ranking(records):
    rows = apply_sales_filters(records, default_filters(), RATES)["rows"]
    monthly = aggregate_by_month(rows)
    growth = calculate_growth(monthly)
    assert round(growth["mom"], 1) == -87.6 and round(growth["yoy"], 1) == -88.5 and growth["trailing12"] is None
    products = aggregate_by_product(rows)
    assert products[0]["name"] == "Unmanufactured Tobacco (FCV Leaf)"
    assert round(sum(p["share"] for p in products)) == 100
    decliners = find_decliners(rows, monthly, "customerName")
    assert decliners["window"] == 6 and decliners["items"][0]["change"] == -100
