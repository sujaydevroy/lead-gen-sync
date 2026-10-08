'use client';

import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import { ResponsiveContainer, ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine } from 'recharts';
import { chartColors } from '@/lib/theme';
import { formatCurrency, formatNumber, formatPeriod, formatPeriodShort } from '@/lib/format';
import ChartTooltip from '@/components/charts/ChartTooltip';

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

/**
 * Historical monthly sales (solid) + 12-month forecast (dashed) with its 95% range (band + bound lines).
 * rows = [{ period, actual?, forecast?, lower?, upper?, band?: [lower, upper] }]
 */
export default function SalesForecastChart({ rows, currency, lastActualPeriod, hasForecast, scenarioLabel }) {
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
      <ResponsiveContainer width="100%" height={360}>
        <ComposedChart data={rows} margin={{ top: 16, right: 16, bottom: 0, left: 4 }}>
          <CartesianGrid vertical={false} stroke={chartColors.grid} />
          <XAxis
            dataKey="period"
            tickFormatter={formatPeriodShort}
            tick={{ fill: chartColors.axis, fontSize: 12 }}
            axisLine={{ stroke: chartColors.grid }}
            tickLine={false}
            minTickGap={16}
          />
          <YAxis
            tickFormatter={(v) => formatNumber(v, { compact: true })}
            tick={{ fill: chartColors.axis, fontSize: 12 }}
            axisLine={false}
            tickLine={false}
            width={60}
          />
          <Tooltip
            cursor={{ stroke: chartColors.axis, strokeDasharray: '3 3' }}
            content={({ active, payload, label }) => {
              if (!active || !payload?.length) return null;
              const row = payload[0].payload;
              const isForecastPoint = row.actual === undefined;
              const items = [];
              if (row.actual !== undefined) items.push({ label: 'Actual', value: formatCurrency(row.actual, currency), color: ACTUAL });
              if (isForecastPoint && row.forecast !== undefined) {
                items.push({ label: `Forecast (${scenarioLabel})`, value: formatCurrency(row.forecast, currency), color: FORECAST, dashed: true });
                items.push({ label: 'Lower bound (95%)', value: formatCurrency(row.lower, currency) });
                items.push({ label: 'Upper bound (95%)', value: formatCurrency(row.upper, currency) });
              }
              return <ChartTooltip title={`${formatPeriod(label)}${isForecastPoint ? ' · forecast' : ''}`} rows={items} />;
            }}
          />
          {hasForecast && (
            <>
              <Area dataKey="band" stroke="none" fill={FORECAST} fillOpacity={0.14} isAnimationActive={false} connectNulls activeDot={false} />
              <Line dataKey="lower" stroke={FORECAST} strokeOpacity={0.55} strokeWidth={1} strokeDasharray="2 3" dot={false} activeDot={false} isAnimationActive={false} />
              <Line dataKey="upper" stroke={FORECAST} strokeOpacity={0.55} strokeWidth={1} strokeDasharray="2 3" dot={false} activeDot={false} isAnimationActive={false} />
              <ReferenceLine
                x={lastActualPeriod}
                stroke={chartColors.axis}
                strokeDasharray="4 4"
                label={{ value: 'Forecast →', position: 'insideTopRight', fill: chartColors.axis, fontSize: 12 }}
              />
            </>
          )}
          <Line
            dataKey="actual"
            stroke={ACTUAL}
            strokeWidth={2}
            dot={{ r: 2.5, fill: ACTUAL, strokeWidth: 0 }}
            activeDot={{ r: 5, stroke: '#fff', strokeWidth: 2 }}
            isAnimationActive={false}
          />
          {hasForecast && (
            <Line
              dataKey="forecast"
              stroke={FORECAST}
              strokeWidth={2}
              strokeDasharray="6 4"
              dot={false}
              activeDot={{ r: 5, stroke: '#fff', strokeWidth: 2, fill: FORECAST }}
              isAnimationActive={false}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </Box>
  );
}
