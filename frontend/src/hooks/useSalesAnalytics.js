import { useMemo } from 'react';
import { useSelector } from 'react-redux';
import {
  applySalesFilters,
  aggregateByMonth,
  aggregateByProduct,
  aggregateByDealer,
  aggregateByRegion,
  calculateKpis,
  concentration,
  findDecliners,
  getSalesOptions,
} from '@/lib/salesAnalytics';
import { generateForecast, scenarioValues, forecastGrowth, buildForecastChartRows } from '@/lib/salesForecast';

// Forecast fitting runs a parameter grid search; cache the latest result so returning
// to the page (component remount) with the same data does not refit the model.
let forecastCache = null;
function cachedForecast(series) {
  const key = series.map((p) => `${p.period}:${p.value}`).join('|');
  if (!forecastCache || forecastCache.key !== key) forecastCache = { key, value: generateForecast(series) };
  return forecastCache.value;
}

/**
 * Central data-processing layer for the Sales Forecast & Analytics page.
 * Reads the uploaded dataset + shared filters from Redux and derives every metric once.
 */
export default function useSalesAnalytics() {
  const { processedData, filters, chartConfig, forecast: forecastState } = useSelector((state) => state.sales);
  const { fxRates } = chartConfig;
  const scenario = forecastState.scenario;

  const options = useMemo(() => getSalesOptions(processedData), [processedData]);

  const base = useMemo(() => {
    const filtered = applySalesFilters(processedData, filters, fxRates);
    const monthly = aggregateByMonth(filtered.rows);
    const products = aggregateByProduct(filtered.rows);
    const dealers = aggregateByDealer(filtered.rows);
    const regions = aggregateByRegion(filtered.rows);
    return {
      filtered,
      monthly,
      products,
      dealers,
      regions,
      kpis: calculateKpis(filtered.rows, monthly, products, dealers),
      dealerConcentration: concentration(dealers, 3),
      productConcentration: concentration(products, 3),
      decliningDealers: findDecliners(filtered.rows, monthly, 'customerName'),
      decliningProducts: findDecliners(filtered.rows, monthly, 'product'),
    };
  }, [processedData, filters, fxRates]);

  const forecast = useMemo(() => cachedForecast(base.monthly), [base.monthly]);

  const scenarioResult = useMemo(() => {
    if (forecast.status !== 'ok') return { chartRows: buildForecastChartRows(base.monthly, null), total: null, growth: null };
    const values = scenarioValues(forecast, scenario);
    const total = values.reduce((s, p) => s + p.value, 0);
    return {
      chartRows: buildForecastChartRows(base.monthly, forecast, scenario),
      total,
      growth: forecastGrowth(base.monthly, total),
    };
  }, [forecast, base.monthly, scenario]);

  return {
    hasData: processedData.length > 0,
    options,
    filters,
    scenario,
    currency: base.filtered.currency,
    converted: base.filtered.converted,
    excludedRows: base.filtered.excludedRows,
    unknownCurrencies: base.filtered.unknownCurrencies,
    rows: base.filtered.rows,
    ...base,
    forecast,
    ...scenarioResult,
  };
}
