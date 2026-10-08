'use client';

import { useMemo } from 'react';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import { chartColors } from '@/lib/theme';
import { formatCurrency, formatPeriod, formatPeriodShort } from '@/lib/format';
import EChart from '@/components/charts/EChart';
import { baseOption, linePointer, tooltipHtml, valueAxis } from '@/components/charts/chartOptions';

const ACTUAL = chartColors.series1;
const FORECAST = chartColors.series2;

function LegendItem({ color, dashed, band, label }) {
  return (
    <Stack direction="row" spacing={0.75} sx={{ alignItems: 'center' }}>
      {band ? (
        <Box aria-hidden sx={{ width: 16, height: 10, bgcolor: color, opacity: 0.18, borderRadius: 0.5 }} />
      ) : (
        <Box aria-hidden sx={{ width: 18, height: 0, borderTop: `2px ${dashed ? 'dashed' : 'solid'} ${color}` }} />
      )}
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
    </Stack>
  );
}

const valueOrNull = (v) => (v === undefined ? null : v);

/** Thin dashed bound line (lower / upper edge of the 95% range). */
const boundLine = (data) => ({
  type: 'line',
  data,
  symbol: 'none',
  lineStyle: { color: FORECAST, opacity: 0.55, width: 1, type: [2, 3] },
  emphasis: { disabled: true },
  tooltip: { show: false },
});

/**
 * Historical monthly sales (solid) + 12-month forecast (dashed) with its 95% range (band + bound lines).
 * rows = [{ period, actual?, forecast?, lower?, upper?, band?: [lower, upper] }]
 */
export default function SalesForecastChart({ rows, currency, lastActualPeriod, hasForecast, scenarioLabel }) {
  const option = useMemo(() => {
    const series = [];
    if (hasForecast) {
      // 95% band = invisible lower line + (upper − lower) stacked on top of it with a fill.
      series.push(
        {
          type: 'line',
          stack: 'band',
          data: rows.map((r) => (r.band ? r.band[0] : null)),
          symbol: 'none',
          lineStyle: { opacity: 0 },
          emphasis: { disabled: true },
        },
        {
          type: 'line',
          stack: 'band',
          data: rows.map((r) => (r.band ? r.band[1] - r.band[0] : null)),
          symbol: 'none',
          lineStyle: { opacity: 0 },
          areaStyle: { color: FORECAST, opacity: 0.14 },
          emphasis: { disabled: true },
        },
        boundLine(rows.map((r) => valueOrNull(r.lower))),
        boundLine(rows.map((r) => valueOrNull(r.upper))),
      );
    }
    series.push({
      type: 'line',
      data: rows.map((r) => valueOrNull(r.actual)),
      lineStyle: { color: ACTUAL, width: 2 },
      itemStyle: { color: ACTUAL },
      symbol: 'circle',
      symbolSize: 5,
      emphasis: { scale: 2, itemStyle: { borderColor: '#fff', borderWidth: 2 } },
    });
    if (hasForecast) {
      series.push({
        type: 'line',
        data: rows.map((r) => valueOrNull(r.forecast)),
        lineStyle: { color: FORECAST, width: 2, type: [6, 4] },
        itemStyle: { color: FORECAST, borderColor: '#fff', borderWidth: 2 },
        symbol: 'circle',
        symbolSize: 10,
        showSymbol: false,
        markLine: {
          silent: true,
          symbol: 'none',
          data: [{ xAxis: lastActualPeriod }],
          lineStyle: { color: chartColors.axis, type: [4, 4], width: 1 },
          label: { formatter: 'Forecast →', position: 'end', color: chartColors.axis, fontSize: 12 },
        },
      });
    }

    return {
      ...baseOption({
        axisPointer: linePointer,
        formatter: (params) => {
          const row = rows[params[0].dataIndex];
          const isForecastPoint = row.actual === undefined;
          const items = [];
          if (row.actual !== undefined) items.push({ label: 'Actual', value: formatCurrency(row.actual, currency), color: ACTUAL });
          if (isForecastPoint && row.forecast !== undefined) {
            items.push({ label: `Forecast (${scenarioLabel})`, value: formatCurrency(row.forecast, currency), color: FORECAST, dashed: true });
            items.push({ label: 'Lower bound (95%)', value: formatCurrency(row.lower, currency) });
            items.push({ label: 'Upper bound (95%)', value: formatCurrency(row.upper, currency) });
          }
          return tooltipHtml(`${formatPeriod(row.period)}${isForecastPoint ? ' · forecast' : ''}`, items);
        },
      }),
      grid: { top: 28, right: 16, bottom: 8, left: 4, containLabel: true },
      xAxis: {
        type: 'category',
        data: rows.map((r) => r.period),
        boundaryGap: false,
        axisLabel: { color: chartColors.axis, fontSize: 12, formatter: formatPeriodShort, hideOverlap: true },
        axisLine: { lineStyle: { color: chartColors.grid } },
        axisTick: { show: false },
      },
      yAxis: valueAxis,
      series,
    };
  }, [rows, currency, lastActualPeriod, hasForecast, scenarioLabel]);

  return (
    <Box>
      <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 2, mb: 1.5 }} aria-label="Chart legend">
        <LegendItem color={ACTUAL} label="Actual sales" />
        {hasForecast && (
          <>
            <LegendItem color={FORECAST} dashed label={`Forecast (${scenarioLabel})`} />
            <LegendItem color={FORECAST} band label="95% forecast range (lower – upper bound)" />
          </>
        )}
      </Stack>
      <EChart option={option} height={360} ariaLabel={`Monthly sales and ${hasForecast ? '12-month forecast' : 'history'} in ${currency}`} />
    </Box>
  );
}
