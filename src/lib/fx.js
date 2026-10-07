// Indicative exchange rates used ONLY to put mixed-currency sales on one scale when
// the user analyses "All currencies". They are static reference values (USD per 1 unit),
// not live market data — users can edit them on the Upload Sales page, or pick a single
// currency to avoid conversion entirely. Replace with a rates API in production.

export const FX_RATES_AS_OF = '2026-10-01';

/** USD value of one unit of each currency. */
export const DEFAULT_FX_RATES_TO_USD = {
  USD: 1,
  EUR: 1.08,
  GBP: 1.27,
  INR: 0.012,
  AED: 0.2723,
  SGD: 0.74,
  AUD: 0.66,
  CAD: 0.73,
  JPY: 0.0067,
};

/**
 * Convert an amount between currencies using USD-based rates.
 * @returns {number|null} null when either currency has no rate
 */
export function convertAmount(amount, from, to, rates) {
  if (from === to) return amount;
  const fromRate = rates[from];
  const toRate = rates[to];
  if (!fromRate || !toRate) return null;
  return (amount * fromRate) / toRate;
}
