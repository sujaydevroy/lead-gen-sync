"""Port of frontend/src/lib/salesForecast.js — transparent, dependency-free sales forecasting.

Model selection (continuous monthly series of length n):
  n >= 24 (and >= 18 months with sales) -> Holt-Winters additive, 12-month seasonality
  n >= 6                                -> SES / Holt linear / Holt damped, lowest AICc wins
  n >= 3                                -> least-squares linear trend
  otherwise / too sparse                -> no forecast ("insufficient")

Monthly bounds are 95% prediction intervals from one-step-ahead residuals. Conservative /
Optimistic scenarios are the 16th / 84th percentiles of 2,000 simulated 12-month totals, using
the same seeded PRNG as the frontend so both return the same numbers.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

from app.services.analytics.jsmath import js_number_str, js_round_4, js_sum
from app.services.analytics.sales_analytics import add_months

FORECAST_HORIZON = 12
MIN_MONTHS_FOR_FORECAST = 3
Z_95 = 1.96
SIMULATION_PATHS = 2000
MASK = 0xFFFFFFFF

SCENARIOS = {
    "conservative": {"label": "Conservative", "description": "16th percentile of 2,000 simulated 12-month totals"},
    "base": {"label": "Base", "description": "Statistical point forecast"},
    "optimistic": {"label": "Optimistic", "description": "84th percentile of 2,000 simulated 12-month totals"},
}

T_975 = [
    12.706,
    4.303,
    3.182,
    2.776,
    2.571,
    2.447,
    2.365,
    2.306,
    2.262,
    2.228,
    2.201,
    2.179,
    2.16,
    2.145,
    2.131,
    2.12,
    2.11,
    2.101,
    2.093,
    2.086,
    2.08,
    2.074,
    2.069,
    2.064,
    2.06,
    2.056,
    2.052,
    2.048,
    2.045,
    2.042,
]


def _t_quantile(df: int) -> float:
    return T_975[df - 1] if 1 <= df <= 30 else Z_95


def _grid(start: float, stop: float, step: float) -> list[float]:
    values = []
    v = start
    while v <= stop + 1e-9:
        values.append(js_round_4(v))
        v += step
    return values


def _aicc(sse: float, n: int, k: int) -> float:
    if n - k - 1 <= 0 or sse <= 0:
        return math.inf
    return n * math.log(sse / n) + 2 * k + (2 * k * (k + 1)) / (n - k - 1)


# ---------------------------------------------------------------------------
# Deterministic PRNG: mulberry32 + Box-Muller (bit-for-bit port of the JavaScript version)
# ---------------------------------------------------------------------------


def _imul(a: int, b: int) -> int:
    return ((a & MASK) * (b & MASK)) & MASK


def _utf16_code_units(text: str):
    """What String.prototype.charCodeAt iterates over."""
    for ch in text:
        cp = ord(ch)
        if cp > 0xFFFF:
            cp -= 0x10000
            yield 0xD800 + (cp >> 10)
            yield 0xDC00 + (cp & 0x3FF)
        else:
            yield cp


def create_normal_sampler(seed_text: str) -> Callable[[], float]:
    seed = 2166136261
    for char_code in _utf16_code_units(seed_text):
        seed = _imul(seed ^ char_code, 16777619)
    state = [seed]

    def uniform() -> float:
        state[0] = (state[0] + 0x6D2B79F5) & MASK
        t = state[0]
        t = _imul(t ^ (t >> 15), t | 1)
        t = (t ^ ((t + _imul(t ^ (t >> 7), t | 61)) & MASK)) & MASK
        return ((t ^ (t >> 14)) & MASK) / 4294967296

    def normal() -> float:
        u = max(uniform(), 1e-12)
        return math.sqrt(-2 * math.log(u)) * math.cos(2 * math.pi * uniform())

    return normal


def _percentile(sorted_values: list[float], p: float) -> float:
    index = (len(sorted_values) - 1) * p
    lo, hi = math.floor(index), math.ceil(index)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (index - lo)


# ---------------------------------------------------------------------------
# Simple exponential smoothing
# ---------------------------------------------------------------------------


def _run_ses(y: list[float], alpha: float) -> dict:
    level = y[0]
    sse = 0
    for t in range(1, len(y)):
        error = y[t] - level
        sse += error * error
        level += alpha * error
    return {"sse": sse, "level": level, "errors": len(y) - 1}


def _fit_ses(y: list[float]) -> dict:
    best = None
    for alpha in _grid(0.05, 0.95, 0.05):
        fit = _run_ses(y, alpha)
        if best is None or fit["sse"] < best["sse"]:
            best = {**fit, "alpha": alpha}
    alpha, level, sse, errors = best["alpha"], best["level"], best["sse"], best["errors"]
    sigma = math.sqrt(sse / max(1, errors - 1))
    points = [
        {"h": h, "forecast": level, "se": sigma * math.sqrt(1 + (h - 1) * alpha * alpha)} for h in range(1, FORECAST_HORIZON + 1)
    ]

    def simulate(normal):
        lvl = level
        out = []
        for _ in points:
            e = sigma * normal()
            out.append(lvl + e)
            lvl += alpha * e
        return out

    return {
        "method": "ses",
        "methodLabel": "Simple exponential smoothing (level, no trend)",
        "params": {"alpha": alpha},
        "sigma": sigma,
        "z": Z_95,
        "points": points,
        "aicc": _aicc(sse, errors, 2),
        "simulate": simulate,
    }


# ---------------------------------------------------------------------------
# Holt's linear (optionally damped) trend
# ---------------------------------------------------------------------------


def _run_holt(y: list[float], alpha: float, beta: float, phi: float) -> dict:
    level = y[0]
    trend = y[1] - y[0] if len(y) > 1 else 0
    sse = 0
    for t in range(1, len(y)):
        forecast = level + phi * trend
        error = y[t] - forecast
        sse += error * error
        level = forecast + alpha * error
        trend = phi * trend + alpha * beta * error
    return {"sse": sse, "level": level, "trend": trend, "errors": len(y) - 1}


def _fit_holt(y: list[float], damped: bool) -> dict:
    best = None
    for alpha in _grid(0.05, 0.95, 0.05):
        for beta in _grid(0.05, 0.95, 0.05):
            for phi in [0.8, 0.85, 0.9, 0.95, 0.98] if damped else [1]:
                fit = _run_holt(y, alpha, beta, phi)
                if best is None or fit["sse"] < best["sse"]:
                    best = {**fit, "alpha": alpha, "beta": beta, "phi": phi}
    param_count = 5 if damped else 4
    dof = max(1, best["errors"] - (param_count - 2))
    sigma = math.sqrt(best["sse"] / dof)
    alpha, beta, phi, level, trend = best["alpha"], best["beta"], best["phi"], best["level"], best["trend"]

    points = []
    phi_sum = 0
    variance_factor = 1
    for h in range(1, FORECAST_HORIZON + 1):
        phi_sum += phi**h
        if h > 1:
            j = h - 1
            phi_j = j if phi == 1 else (phi * (1 - phi**j)) / (1 - phi)
            c = alpha * (1 + beta * phi_j)
            variance_factor += c * c
        points.append({"h": h, "forecast": level + phi_sum * trend, "se": sigma * math.sqrt(variance_factor)})

    def simulate(normal):
        lvl, b = level, trend
        out = []
        for _ in points:
            e = sigma * normal()
            out.append(lvl + phi * b + e)
            lvl = lvl + phi * b + alpha * e
            b = phi * b + alpha * beta * e
        return out

    label = "Holt's damped-trend exponential smoothing" if phi < 1 else "Holt's linear-trend exponential smoothing"
    return {
        "method": "holt",
        "methodLabel": label,
        "params": {"alpha": alpha, "beta": beta, "phi": phi},
        "sigma": sigma,
        "z": Z_95,
        "points": points,
        "aicc": _aicc(best["sse"], best["errors"], param_count),
        "simulate": simulate,
    }


def _fit_exponential_smoothing(y: list[float]) -> dict:
    candidates = [_fit_ses(y), _fit_holt(y, False), _fit_holt(y, True)]
    chosen = candidates[0]
    for candidate in candidates[1:]:
        if candidate["aicc"] < chosen["aicc"]:
            chosen = candidate
    return {**chosen, "candidates": [{"method": c["methodLabel"], "aicc": c["aicc"]} for c in candidates]}


# ---------------------------------------------------------------------------
# Holt-Winters additive (m = 12)
# ---------------------------------------------------------------------------


def _run_holt_winters(y: list[float], alpha: float, beta: float, gamma: float, m: int) -> dict:
    def mean(values):
        return js_sum(values) / len(values)

    level = mean(y[:m])
    trend = (mean(y[m : 2 * m]) - level) / m
    season = [v - level for v in y[:m]]
    sse = 0
    for t in range(m, len(y)):
        s = season[t - m]
        forecast = level + trend + s
        error = y[t] - forecast
        sse += error * error
        level = level + trend + alpha * error
        trend = trend + alpha * beta * error
        season.append(s + gamma * error)
    return {"sse": sse, "level": level, "trend": trend, "season": season, "errors": len(y) - m}


def _fit_holt_winters(y: list[float], m: int = 12) -> dict:
    best = None
    for alpha in _grid(0.1, 0.9, 0.1):
        for beta in _grid(0.05, 0.5, 0.05):
            for gamma in _grid(0.1, 0.9, 0.1):
                fit = _run_holt_winters(y, alpha, beta, gamma, m)
                if best is None or fit["sse"] < best["sse"]:
                    best = {**fit, "alpha": alpha, "beta": beta, "gamma": gamma}
    dof = max(1, best["errors"] - 3)
    sigma = math.sqrt(best["sse"] / dof)
    alpha, beta, gamma = best["alpha"], best["beta"], best["gamma"]
    level, trend, season = best["level"], best["trend"], best["season"]
    n = len(y)
    points = []
    variance_factor = 1
    for h in range(1, FORECAST_HORIZON + 1):
        if h > 1:
            j = h - 1
            c = alpha * (1 + j * beta) + (gamma if j % m == 0 else 0)
            variance_factor += c * c
        s = season[n - m + ((h - 1) % m)]
        points.append({"h": h, "forecast": level + h * trend + s, "se": sigma * math.sqrt(variance_factor)})

    def simulate(normal):
        lvl, b, seas = level, trend, list(season)
        out = []
        for _ in points:
            e = sigma * normal()
            seasonal = seas[len(seas) - m]
            out.append(lvl + b + seasonal + e)
            lvl = lvl + b + alpha * e
            b = b + alpha * beta * e
            seas.append(seasonal + gamma * e)
        return out

    return {
        "method": "holt-winters",
        "methodLabel": "Holt-Winters additive exponential smoothing (12-month seasonality)",
        "params": {"alpha": alpha, "beta": beta, "gamma": gamma},
        "sigma": sigma,
        "z": Z_95,
        "points": points,
        "simulate": simulate,
    }


# ---------------------------------------------------------------------------
# OLS linear trend (short histories)
# ---------------------------------------------------------------------------


def _fit_linear_trend(y: list[float]) -> dict:
    n = len(y)
    x_mean = (n - 1) / 2
    y_mean = js_sum(y) / n
    sxx = js_sum((x - x_mean) ** 2 for x in range(n))
    slope = js_sum((x - x_mean) * (y[x] - y_mean) for x in range(n)) / sxx
    intercept = y_mean - slope * x_mean
    ssr = js_sum((v - (intercept + slope * i)) ** 2 for i, v in enumerate(y))
    dof = n - 2
    sigma = math.sqrt(ssr / max(1, dof))
    z = _t_quantile(dof)
    points = []
    for h in range(1, FORECAST_HORIZON + 1):
        x0 = n - 1 + h
        points.append({"h": h, "forecast": intercept + slope * x0, "se": sigma * math.sqrt(1 + 1 / n + (x0 - x_mean) ** 2 / sxx)})

    def simulate(normal):
        return [p["forecast"] + p["se"] * normal() for p in points]

    return {
        "method": "linear",
        "methodLabel": "Linear trend (least squares) — short history, trend-based estimate only",
        "params": {"slope": slope, "intercept": intercept},
        "sigma": sigma,
        "z": z,
        "points": points,
        "simulate": simulate,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_forecast(monthly: list[dict]) -> dict[str, Any]:
    n = len(monthly)
    active_months = sum(1 for p in monthly if p["value"] > 0)

    if n < MIN_MONTHS_FOR_FORECAST or active_months < MIN_MONTHS_FOR_FORECAST:
        return {
            "status": "insufficient",
            "historyMonths": n,
            "reason": (
                "Not enough historical sales data is available to generate a reliable 12-month forecast. "
                f"At least {MIN_MONTHS_FOR_FORECAST} months with recorded sales are required (found {active_months}). "
                "Add more dated transaction records to enable forecasting."
            ),
        }
    if active_months / n < 0.5:
        return {
            "status": "insufficient",
            "historyMonths": n,
            "reason": (
                f"Sales are too sparse for a reliable forecast: only {active_months} of {n} months in the selected "
                "range have recorded sales. Widen the filters or add more transaction records."
            ),
        }

    y = [p["value"] for p in monthly]
    if n >= 24 and active_months >= 18:
        model = _fit_holt_winters(y)
    elif n >= 6:
        model = _fit_exponential_smoothing(y)
    else:
        model = _fit_linear_trend(y)

    normal = create_normal_sampler("|".join(f"{p['period']}:{js_number_str(p['value'])}" for p in monthly))
    totals = []
    for _ in range(SIMULATION_PATHS):
        totals.append(js_sum(max(0, v) for v in model["simulate"](normal)))
    totals.sort()

    base_total = js_sum(max(0, p["forecast"]) for p in model["points"])
    scenario_totals = {
        "conservative": min(_percentile(totals, 0.16), base_total),
        "base": base_total,
        "optimistic": max(_percentile(totals, 0.84), base_total),
    }
    conservative_scale = scenario_totals["conservative"] / base_total if base_total > 0 else None
    optimistic_scale = scenario_totals["optimistic"] / base_total if base_total > 0 else None

    last_period = monthly[-1]["period"]
    points = []
    for p in model["points"]:
        forecast, se = p["forecast"], p["se"]
        base = max(0, forecast)
        points.append(
            {
                "period": add_months(last_period, p["h"]),
                "forecast": base,
                "lower": max(0, forecast - model["z"] * se),
                "upper": max(0, forecast + model["z"] * se),
                "conservative": (
                    scenario_totals["conservative"] / FORECAST_HORIZON
                    if conservative_scale is None
                    else base * conservative_scale
                ),
                "optimistic": (
                    scenario_totals["optimistic"] / FORECAST_HORIZON if optimistic_scale is None else base * optimistic_scale
                ),
                "se": se,
                "clampedAtZero": forecast < 0,
            }
        )

    result = {k: v for k, v in model.items() if k not in ("simulate", "points")}
    return {
        "status": "ok",
        **result,
        "historyMonths": n,
        "activeMonths": active_months,
        "points": points,
        "scenarioTotals": scenario_totals,
    }


def scenario_values(forecast: dict, scenario: str = "base") -> list[dict]:
    if not forecast or forecast.get("status") != "ok":
        return []
    key = scenario if scenario in ("conservative", "optimistic") else "forecast"
    return [{**p, "value": p[key]} for p in forecast["points"]]


def forecast_growth(monthly: list[dict], forecast_total: float | None) -> dict | None:
    n = len(monthly)
    if not n or forecast_total is None:
        return None
    if n >= 12:
        comparable = js_sum(p["value"] for p in monthly[-12:])
        basis = "last 12 months of actual sales"
    else:
        comparable = (js_sum(p["value"] for p in monthly) / n) * 12
        basis = f"annualised average of the {n} available month{'' if n == 1 else 's'}"
    return {
        "comparable": comparable,
        "basis": basis,
        "growth": ((forecast_total - comparable) / comparable) * 100 if comparable > 0 else None,
    }


def build_forecast_chart_rows(monthly: list[dict], forecast: dict | None, scenario: str = "base") -> list[dict]:
    rows = [{"period": p["period"], "actual": p["value"]} for p in monthly]
    if not forecast or forecast.get("status") != "ok" or not rows:
        return rows
    last = rows[-1]
    last["forecast"] = last["actual"]
    last["band"] = [last["actual"], last["actual"]]
    for p in scenario_values(forecast, scenario):
        rows.append(
            {
                "period": p["period"],
                "forecast": p["value"],
                "lower": p["lower"],
                "upper": p["upper"],
                "band": [p["lower"], p["upper"]],
            }
        )
    return rows
