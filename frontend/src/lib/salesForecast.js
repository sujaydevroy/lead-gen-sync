// Transparent, dependency-free sales forecasting.
//
// Model selection (by length of the continuous monthly series, n):
//   n >= 24 (and >= 18 months with sales) -> Holt-Winters additive, 12-month seasonality
//   n >= 6                                -> exponential smoothing: simple (level), Holt linear
//                                            or Holt damped trend, whichever has the lowest AICc
//   n >= 3                                -> ordinary least-squares linear trend
//   otherwise / too sparse                -> no forecast ("insufficient")
//
// Smoothing parameters are chosen by grid search minimising the in-sample one-step-ahead
// squared error; AICc then penalises extra parameters so a trend is only used when the data
// supports it. Monthly forecast bounds are 95% prediction intervals derived from those residuals.
//
// Conservative / Optimistic scenarios come from the uncertainty of the 12-month TOTAL:
// 2,000 future paths are simulated from the fitted model (Gaussian errors with the model's
// residual σ, seeded so results are repeatable), sales are floored at 0, and the 16th / 84th
// percentiles of the simulated totals (≈ ∓1 standard deviation) define the scenarios.
import { addMonths } from '@/lib/salesAnalytics';

export const FORECAST_HORIZON = 12;
export const MIN_MONTHS_FOR_FORECAST = 3;
export const Z_95 = 1.96;
export const SIMULATION_PATHS = 2000;

export const SCENARIOS = {
  conservative: { label: 'Conservative', description: '16th percentile of 2,000 simulated 12-month totals' },
  base: { label: 'Base', description: 'Statistical point forecast' },
  optimistic: { label: 'Optimistic', description: '84th percentile of 2,000 simulated 12-month totals' },
};

// Deterministic PRNG (mulberry32) + Box-Muller standard normal draws.
function createNormalSampler(seedText) {
  let seed = 2166136261;
  for (let i = 0; i < seedText.length; i += 1) seed = Math.imul(seed ^ seedText.charCodeAt(i), 16777619) >>> 0;
  const uniform = () => {
    seed = (seed + 0x6d2b79f5) >>> 0;
    let t = seed;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  return () => {
    const u = Math.max(uniform(), 1e-12);
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * uniform());
  };
}

function percentile(sorted, p) {
  const index = (sorted.length - 1) * p;
  const lo = Math.floor(index);
  const hi = Math.ceil(index);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (index - lo);
}

const grid = (from, to, step) => {
  const values = [];
  for (let v = from; v <= to + 1e-9; v += step) values.push(Number(v.toFixed(4)));
  return values;
};

// Two-sided 97.5% Student-t quantiles for small samples (df 1-30).
const T_975 = [12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228, 2.201, 2.179, 2.16, 2.145, 2.131,
  2.12, 2.11, 2.101, 2.093, 2.086, 2.08, 2.074, 2.069, 2.064, 2.06, 2.056, 2.052, 2.048, 2.045, 2.042];
const tQuantile = (df) => (df >= 1 && df <= 30 ? T_975[df - 1] : Z_95);

/**
 * Corrected Akaike information criterion for a Gaussian-error model fitted by SSE.
 * Lets us prefer a simpler model unless extra parameters genuinely improve the fit.
 */
function aicc(sse, n, k) {
  if (n - k - 1 <= 0 || sse <= 0) return Infinity;
  return n * Math.log(sse / n) + 2 * k + (2 * k * (k + 1)) / (n - k - 1);
}

// ---------------------------------------------------------------------------
// Simple exponential smoothing (level only)
// ---------------------------------------------------------------------------

function runSes(y, alpha) {
  let level = y[0];
  let sse = 0;
  for (let t = 1; t < y.length; t += 1) {
    const error = y[t] - level;
    sse += error * error;
    level += alpha * error;
  }
  return { sse, level, errors: y.length - 1 };
}

function fitSes(y) {
  let best = null;
  for (const alpha of grid(0.05, 0.95, 0.05)) {
    const fit = runSes(y, alpha);
    if (!best || fit.sse < best.sse) best = { ...fit, alpha };
  }
  const { alpha, level, sse, errors } = best;
  const sigma = Math.sqrt(sse / Math.max(1, errors - 1));
  const points = [];
  for (let h = 1; h <= FORECAST_HORIZON; h += 1) {
    // Var_h = σ² (1 + (h − 1) α²)
    points.push({ h, forecast: level, se: sigma * Math.sqrt(1 + (h - 1) * alpha * alpha) });
  }
  return {
    method: 'ses',
    methodLabel: 'Simple exponential smoothing (level, no trend)',
    params: { alpha },
    sigma,
    z: Z_95,
    points,
    aicc: aicc(sse, errors, 2),
    simulate(normal) {
      let l = level;
      return points.map(() => {
        const e = sigma * normal();
        const value = l + e;
        l += alpha * e;
        return value;
      });
    },
  };
}

// ---------------------------------------------------------------------------
// Holt's linear (optionally damped) trend
// ---------------------------------------------------------------------------

function runHolt(y, alpha, beta, phi) {
  let level = y[0];
  let trend = y.length > 1 ? y[1] - y[0] : 0;
  let sse = 0;
  for (let t = 1; t < y.length; t += 1) {
    const forecast = level + phi * trend;
    const error = y[t] - forecast;
    sse += error * error;
    level = forecast + alpha * error;
    trend = phi * trend + alpha * beta * error;
  }
  return { sse, level, trend, errors: y.length - 1 };
}

function fitHolt(y, damped) {
  let best = null;
  for (const alpha of grid(0.05, 0.95, 0.05)) {
    for (const beta of grid(0.05, 0.95, 0.05)) {
      for (const phi of damped ? [0.8, 0.85, 0.9, 0.95, 0.98] : [1]) {
        const fit = runHolt(y, alpha, beta, phi);
        if (!best || fit.sse < best.sse) best = { ...fit, alpha, beta, phi };
      }
    }
  }
  const paramCount = damped ? 5 : 4; // alpha, beta, (phi), initial level, initial trend
  const dof = Math.max(1, best.errors - (paramCount - 2));
  const sigma = Math.sqrt(best.sse / dof);
  const { alpha, beta, phi, level, trend } = best;

  const points = [];
  let phiSum = 0;
  let varianceFactor = 1;
  for (let h = 1; h <= FORECAST_HORIZON; h += 1) {
    phiSum += phi ** h;
    if (h > 1) {
      // c_j = alpha * (1 + beta * (phi + phi^2 + ... + phi^j)), j = h-1
      const j = h - 1;
      const phiJ = phi === 1 ? j : (phi * (1 - phi ** j)) / (1 - phi);
      const c = alpha * (1 + beta * phiJ);
      varianceFactor += c * c;
    }
    points.push({ h, forecast: level + phiSum * trend, se: sigma * Math.sqrt(varianceFactor) });
  }
  return {
    method: 'holt',
    methodLabel: phi < 1 ? "Holt's damped-trend exponential smoothing" : "Holt's linear-trend exponential smoothing",
    params: { alpha, beta, phi },
    sigma,
    z: Z_95,
    points,
    aicc: aicc(best.sse, best.errors, paramCount),
    simulate(normal) {
      let l = level;
      let b = trend;
      return points.map(() => {
        const e = sigma * normal();
        const value = l + phi * b + e;
        l = l + phi * b + alpha * e;
        b = phi * b + alpha * beta * e;
        return value;
      });
    },
  };
}

/** Best exponential-smoothing model for 6-23 months: SES vs Holt vs damped Holt, by AICc. */
function fitExponentialSmoothing(y) {
  const candidates = [fitSes(y), fitHolt(y, false), fitHolt(y, true)];
  const chosen = candidates.reduce((best, c) => (c.aicc < best.aicc ? c : best));
  return { ...chosen, candidates: candidates.map((c) => ({ method: c.methodLabel, aicc: c.aicc })) };
}

// ---------------------------------------------------------------------------
// Holt-Winters additive seasonality (m = 12)
// ---------------------------------------------------------------------------

function runHoltWinters(y, alpha, beta, gamma, m) {
  const mean = (arr) => arr.reduce((s, v) => s + v, 0) / arr.length;
  let level = mean(y.slice(0, m));
  let trend = (mean(y.slice(m, 2 * m)) - level) / m;
  const season = y.slice(0, m).map((v) => v - level);
  let sse = 0;
  for (let t = m; t < y.length; t += 1) {
    const s = season[t - m];
    const forecast = level + trend + s;
    const error = y[t] - forecast;
    sse += error * error;
    level = level + trend + alpha * error;
    trend = trend + alpha * beta * error;
    season.push(s + gamma * error);
  }
  return { sse, level, trend, season, errors: y.length - m };
}

function fitHoltWinters(y, m = 12) {
  let best = null;
  for (const alpha of grid(0.1, 0.9, 0.1)) {
    for (const beta of grid(0.05, 0.5, 0.05)) {
      for (const gamma of grid(0.1, 0.9, 0.1)) {
        const fit = runHoltWinters(y, alpha, beta, gamma, m);
        if (!best || fit.sse < best.sse) best = { ...fit, alpha, beta, gamma };
      }
    }
  }
  const dof = Math.max(1, best.errors - 3);
  const sigma = Math.sqrt(best.sse / dof);
  const { alpha, beta, gamma, level, trend, season } = best;
  const n = y.length;
  const points = [];
  let varianceFactor = 1;
  for (let h = 1; h <= FORECAST_HORIZON; h += 1) {
    if (h > 1) {
      const j = h - 1;
      const c = alpha * (1 + j * beta) + (j % m === 0 ? gamma : 0);
      varianceFactor += c * c;
    }
    const s = season[n - m + ((h - 1) % m)];
    points.push({ h, forecast: level + h * trend + s, se: sigma * Math.sqrt(varianceFactor) });
  }
  return {
    method: 'holt-winters',
    methodLabel: 'Holt-Winters additive exponential smoothing (12-month seasonality)',
    params: { alpha, beta, gamma },
    sigma,
    z: Z_95,
    points,
    simulate(normal) {
      let l = level;
      let b = trend;
      const s = [...season];
      return points.map(() => {
        const e = sigma * normal();
        const seasonal = s[s.length - m];
        const value = l + b + seasonal + e;
        l = l + b + alpha * e;
        b = b + alpha * beta * e;
        s.push(seasonal + gamma * e);
        return value;
      });
    },
  };
}

// ---------------------------------------------------------------------------
// OLS linear trend (short histories)
// ---------------------------------------------------------------------------

function fitLinearTrend(y) {
  const n = y.length;
  const xs = y.map((_, i) => i);
  const xMean = (n - 1) / 2;
  const yMean = y.reduce((s, v) => s + v, 0) / n;
  const sxx = xs.reduce((s, x) => s + (x - xMean) ** 2, 0);
  const slope = xs.reduce((s, x, i) => s + (x - xMean) * (y[i] - yMean), 0) / sxx;
  const intercept = yMean - slope * xMean;
  const ssr = y.reduce((s, v, i) => s + (v - (intercept + slope * i)) ** 2, 0);
  const dof = n - 2;
  const sigma = Math.sqrt(ssr / Math.max(1, dof));
  const z = tQuantile(dof);
  const points = [];
  for (let h = 1; h <= FORECAST_HORIZON; h += 1) {
    const x0 = n - 1 + h;
    points.push({
      h,
      forecast: intercept + slope * x0,
      se: sigma * Math.sqrt(1 + 1 / n + (x0 - xMean) ** 2 / sxx),
    });
  }
  return {
    method: 'linear',
    methodLabel: 'Linear trend (least squares) — short history, trend-based estimate only',
    params: { slope, intercept },
    sigma,
    z,
    points,
    // Approximation: monthly errors drawn independently with each month's prediction standard error.
    simulate(normal) {
      return points.map((p) => p.forecast + p.se * normal());
    },
  };
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * @param {{ period: string, value: number }[]} monthlySeries continuous monthly history
 * @returns {{ status: 'ok', method: string, methodLabel: string, params: object, sigma: number,
 *             historyMonths: number, points: object[] } | { status: 'insufficient', reason: string, historyMonths: number }}
 */
export function generateForecast(monthlySeries) {
  const n = monthlySeries.length;
  const activeMonths = monthlySeries.filter((p) => p.value > 0).length;

  if (n < MIN_MONTHS_FOR_FORECAST || activeMonths < MIN_MONTHS_FOR_FORECAST) {
    return {
      status: 'insufficient',
      historyMonths: n,
      reason: `Not enough historical sales data is available to generate a reliable 12-month forecast. At least ${MIN_MONTHS_FOR_FORECAST} months with recorded sales are required (found ${activeMonths}). Add more dated transaction records to enable forecasting.`,
    };
  }
  if (activeMonths / n < 0.5) {
    return {
      status: 'insufficient',
      historyMonths: n,
      reason: `Sales are too sparse for a reliable forecast: only ${activeMonths} of ${n} months in the selected range have recorded sales. Widen the filters or add more transaction records.`,
    };
  }

  const y = monthlySeries.map((p) => p.value);
  let model;
  if (n >= 24 && activeMonths >= 18) model = fitHoltWinters(y);
  else if (n >= 6) model = fitExponentialSmoothing(y);
  else model = fitLinearTrend(y);

  // Simulate future paths to get the distribution of the 12-month total.
  const normal = createNormalSampler(monthlySeries.map((p) => `${p.period}:${p.value}`).join('|'));
  const totals = [];
  for (let i = 0; i < SIMULATION_PATHS; i += 1) {
    totals.push(model.simulate(normal).reduce((sum, v) => sum + Math.max(0, v), 0));
  }
  totals.sort((a, b) => a - b);

  const baseTotal = model.points.reduce((sum, p) => sum + Math.max(0, p.forecast), 0);
  const scenarioTotals = {
    conservative: Math.min(percentile(totals, 0.16), baseTotal),
    base: baseTotal,
    optimistic: Math.max(percentile(totals, 0.84), baseTotal),
  };
  // Scenario paths keep the base forecast's monthly shape, scaled to the scenario total.
  const scale = (total) => (baseTotal > 0 ? total / baseTotal : null);
  const conservativeScale = scale(scenarioTotals.conservative);
  const optimisticScale = scale(scenarioTotals.optimistic);

  const lastPeriod = monthlySeries[n - 1].period;
  const points = model.points.map(({ h, forecast, se }) => {
    const base = Math.max(0, forecast);
    return {
      period: addMonths(lastPeriod, h),
      forecast: base,
      lower: Math.max(0, forecast - model.z * se),
      upper: Math.max(0, forecast + model.z * se),
      conservative: conservativeScale === null ? scenarioTotals.conservative / FORECAST_HORIZON : base * conservativeScale,
      optimistic: optimisticScale === null ? scenarioTotals.optimistic / FORECAST_HORIZON : base * optimisticScale,
      se,
      clampedAtZero: forecast < 0,
    };
  });

  const { simulate, ...serialisableModel } = model;
  return { status: 'ok', ...serialisableModel, historyMonths: n, activeMonths, points, scenarioTotals };
}

/** Forecast values for the selected scenario. */
export function scenarioValues(forecast, scenario = 'base') {
  if (forecast?.status !== 'ok') return [];
  const key = scenario === 'conservative' ? 'conservative' : scenario === 'optimistic' ? 'optimistic' : 'forecast';
  return forecast.points.map((p) => ({ ...p, value: p[key] }));
}

/**
 * Forecast growth = (forecast next 12 months − comparable historical) / comparable historical × 100.
 * Comparable = the last 12 actual months when available, otherwise the average month × 12.
 */
export function forecastGrowth(monthlySeries, forecastTotal) {
  const n = monthlySeries.length;
  if (!n || forecastTotal === null) return null;
  const sum = (list) => list.reduce((s, p) => s + p.value, 0);
  if (n >= 12) {
    const comparable = sum(monthlySeries.slice(-12));
    return {
      comparable,
      basis: 'last 12 months of actual sales',
      growth: comparable > 0 ? ((forecastTotal - comparable) / comparable) * 100 : null,
    };
  }
  const comparable = (sum(monthlySeries) / n) * 12;
  return {
    comparable,
    basis: `annualised average of the ${n} available month${n === 1 ? '' : 's'}`,
    growth: comparable > 0 ? ((forecastTotal - comparable) / comparable) * 100 : null,
  };
}

/** Rows for the actual + forecast chart. The forecast line starts at the last actual point. */
export function buildForecastChartRows(monthlySeries, forecast, scenario = 'base') {
  const rows = monthlySeries.map((p) => ({ period: p.period, actual: p.value }));
  if (forecast?.status !== 'ok' || !rows.length) return rows;
  const last = rows[rows.length - 1];
  last.forecast = last.actual;
  last.band = [last.actual, last.actual];
  scenarioValues(forecast, scenario).forEach((p) => {
    rows.push({
      period: p.period,
      forecast: p.value,
      lower: p.lower,
      upper: p.upper,
      band: [p.lower, p.upper],
    });
  });
  return rows;
}
