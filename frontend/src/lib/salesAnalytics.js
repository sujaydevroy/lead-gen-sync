// Pure sales analytics over parsed SalesRecords. No React, no Redux — so the same
// functions can run on a server or in tests.
import { convertAmount } from '@/lib/fx';
import { ALL_CURRENCIES } from '@/types/sales';

// ---------------------------------------------------------------------------
// Periods
// ---------------------------------------------------------------------------

export function addMonths(period, count) {
  const [y, m] = period.split('-').map(Number);
  const index = y * 12 + (m - 1) + count;
  return `${Math.floor(index / 12)}-${String((index % 12) + 1).padStart(2, '0')}`;
}

export function monthsBetween(from, to) {
  const [fy, fm] = from.split('-').map(Number);
  const [ty, tm] = to.split('-').map(Number);
  return (ty - fy) * 12 + (tm - fm);
}

// ---------------------------------------------------------------------------
// Options + filtering (the single filtering layer shared by every sales view)
// ---------------------------------------------------------------------------

const uniqueSorted = (values) => [...new Set(values.filter(Boolean))].sort((a, b) => a.localeCompare(b));

/** Distinct values available for filter controls. */
export function getSalesOptions(records) {
  const periods = uniqueSorted(records.map((r) => r.period));
  return {
    customers: uniqueSorted(records.map((r) => r.customerName)),
    products: uniqueSorted(records.map((r) => r.product)),
    countries: uniqueSorted(records.map((r) => r.country)),
    currencies: uniqueSorted(records.map((r) => r.currency)),
    firstPeriod: periods[0] || '',
    lastPeriod: periods[periods.length - 1] || '',
  };
}

/**
 * Apply sales filters and express each row's amount in one currency (`value`).
 *
 * - currency = a specific code -> only rows in that currency, no conversion.
 * - currency = ALL -> every row converted to `reportingCurrency` with the given rates;
 *   rows whose currency has no rate are excluded and reported.
 *
 * @param {import('@/types/sales').SalesRecord[]} records
 * @param {import('@/types/sales').SalesFilters} filters
 * @param {Record<string, number>} fxRates
 */
export function applySalesFilters(records, filters, fxRates) {
  const single = filters.currency && filters.currency !== ALL_CURRENCIES;
  const currency = single ? filters.currency : filters.reportingCurrency;
  const unknownCurrencies = new Set();
  let excludedRows = 0;
  const rows = [];

  records.forEach((record) => {
    if (single && record.currency !== filters.currency) return;
    if (filters.dateFrom && record.period < filters.dateFrom) return;
    if (filters.dateTo && record.period > filters.dateTo) return;
    if (filters.customers?.length && !filters.customers.includes(record.customerName)) return;
    if (filters.products?.length && !filters.products.includes(record.product)) return;
    if (filters.countries?.length && !filters.countries.includes(record.country)) return;

    const value = single ? record.amount : convertAmount(record.amount, record.currency, currency, fxRates);
    if (value === null) {
      unknownCurrencies.add(record.currency);
      excludedRows += 1;
      return;
    }
    rows.push({ ...record, value });
  });

  return { rows, currency, converted: !single, excludedRows, unknownCurrencies: [...unknownCurrencies] };
}

// ---------------------------------------------------------------------------
// Aggregations
// ---------------------------------------------------------------------------

/**
 * Continuous monthly series from the first to the last month with sales.
 * Months inside the range with no transactions are 0 (no recorded sales).
 */
export function aggregateByMonth(rows) {
  if (!rows.length) return [];
  const totals = new Map();
  const counts = new Map();
  rows.forEach((r) => {
    totals.set(r.period, (totals.get(r.period) || 0) + r.value);
    counts.set(r.period, (counts.get(r.period) || 0) + 1);
  });
  const periods = [...totals.keys()].sort();
  const first = periods[0];
  const span = monthsBetween(first, periods[periods.length - 1]);
  return Array.from({ length: span + 1 }, (_, i) => {
    const period = addMonths(first, i);
    return { period, value: totals.get(period) || 0, transactions: counts.get(period) || 0 };
  });
}

export function aggregateByQuarter(monthlySeries) {
  const totals = new Map();
  monthlySeries.forEach(({ period, value }) => {
    const [y, m] = period.split('-').map(Number);
    const key = `${y}-Q${Math.ceil(m / 3)}`;
    const entry = totals.get(key) || { quarter: key, value: 0, months: 0 };
    entry.value += value;
    entry.months += 1;
    totals.set(key, entry);
  });
  return [...totals.values()];
}

/**
 * Totals per dimension value, sorted by value (desc), with share of total.
 * @param {'customerName'|'product'|'country'} key
 */
export function aggregateBy(rows, key) {
  const totals = new Map();
  rows.forEach((r) => {
    const entry = totals.get(r[key]) || { name: r[key], value: 0, transactions: 0 };
    entry.value += r.value;
    entry.transactions += 1;
    totals.set(r[key], entry);
  });
  const grandTotal = rows.reduce((sum, r) => sum + r.value, 0);
  return [...totals.values()]
    .map((e) => ({ ...e, share: grandTotal > 0 ? (e.value / grandTotal) * 100 : 0 }))
    .sort((a, b) => b.value - a.value);
}

export const aggregateByProduct = (rows) => aggregateBy(rows, 'product');
export const aggregateByDealer = (rows) => aggregateBy(rows, 'customerName');
export const aggregateByRegion = (rows) => aggregateBy(rows, 'country');

// ---------------------------------------------------------------------------
// Growth + concentration
// ---------------------------------------------------------------------------

export function growthRate(current, previous) {
  if (previous === null || previous === undefined || previous === 0) return null;
  return ((current - previous) / Math.abs(previous)) * 100;
}

/** Month-over-month and year-over-year growth of the latest month. */
export function calculateGrowth(monthlySeries) {
  const n = monthlySeries.length;
  if (n < 2) return { mom: null, yoy: null, trailing12: null, latest: monthlySeries[n - 1] || null };
  const latest = monthlySeries[n - 1];
  const previous = monthlySeries[n - 2];
  const yearAgo = n >= 13 ? monthlySeries[n - 13] : null;
  const sum = (list) => list.reduce((s, p) => s + p.value, 0);
  return {
    latest,
    previous,
    yearAgo,
    mom: growthRate(latest.value, previous.value),
    yoy: yearAgo ? growthRate(latest.value, yearAgo.value) : null,
    // Last 12 months vs the 12 before — needs 24 months of history.
    trailing12: n >= 24 ? growthRate(sum(monthlySeries.slice(-12)), sum(monthlySeries.slice(-24, -12))) : null,
  };
}

/** Share of total held by the top N entries, plus the Herfindahl-Hirschman index (0-10,000). */
export function concentration(ranked, topN = 3) {
  if (!ranked.length) return null;
  const topShare = ranked.slice(0, topN).reduce((s, e) => s + e.share, 0);
  const hhi = ranked.reduce((s, e) => s + e.share * e.share, 0);
  const level = hhi >= 2500 ? 'High' : hhi >= 1500 ? 'Moderate' : 'Low';
  return { topN: Math.min(topN, ranked.length), topShare, hhi, level, entities: ranked.length };
}

/**
 * Entities whose sales fell between two equal windows at the end of the series.
 * Window = 6 months when at least 12 months exist, otherwise half the series.
 * @param {'customerName'|'product'} key
 */
export function findDecliners(rows, monthlySeries, key) {
  const n = monthlySeries.length;
  const window = Math.min(6, Math.floor(n / 2));
  if (window < 1) return { window: 0, items: [] };
  const recentStart = monthlySeries[n - window].period;
  const priorStart = monthlySeries[n - 2 * window].period;
  const recentEnd = monthlySeries[n - 1].period;

  const totals = new Map();
  rows.forEach((r) => {
    if (r.period < priorStart || r.period > recentEnd) return;
    const entry = totals.get(r[key]) || { name: r[key], prior: 0, recent: 0 };
    if (r.period >= recentStart) entry.recent += r.value;
    else entry.prior += r.value;
    totals.set(r[key], entry);
  });

  const items = [...totals.values()]
    .filter((e) => e.prior > 0 && e.recent < e.prior)
    .map((e) => ({ ...e, change: growthRate(e.recent, e.prior) }))
    .sort((a, b) => a.change - b.change);

  return {
    window,
    priorRange: [priorStart, monthlySeries[n - window - 1].period],
    recentRange: [recentStart, recentEnd],
    items,
  };
}

// ---------------------------------------------------------------------------
// KPI bundle
// ---------------------------------------------------------------------------

export function calculateKpis(rows, monthlySeries, products, dealers) {
  const total = rows.reduce((s, r) => s + r.value, 0);
  return {
    totalSales: total,
    transactions: rows.length,
    averageTransactionValue: rows.length ? total / rows.length : null,
    averageMonthlySales: monthlySeries.length ? total / monthlySeries.length : null,
    months: monthlySeries.length,
    topProduct: products[0] || null,
    topDealer: dealers[0] || null,
    growth: calculateGrowth(monthlySeries),
    quarterly: aggregateByQuarter(monthlySeries),
  };
}

/** Everything the Upload Sales charts need, computed once per filter change. */
export function buildSalesChartData(rows) {
  const monthly = aggregateByMonth(rows);
  const products = aggregateByProduct(rows);
  const dealers = aggregateByDealer(rows);
  return {
    monthly,
    products: products.slice(0, 10),
    productCount: products.length,
    countries: aggregateByRegion(rows),
    dealers: dealers.slice(0, 10),
    dealerCount: dealers.length,
    total: rows.reduce((s, r) => s + r.value, 0),
    transactions: rows.length,
  };
}
