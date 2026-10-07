'use client';

import { ResponsiveContainer, ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import { chartColors } from '@/lib/theme';
import { formatCurrency, formatNumber, formatPeriod, formatPeriodShort } from '@/lib/format';
import ChartTooltip from './ChartTooltip';

/** Monthly sales totals as bars or a line. data = [{ period: 'YYYY-MM', value, transactions }] */
export default function MonthlySalesChart({ data, currency, type = 'bar', height = 300 }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 4 }}>
        <CartesianGrid vertical={false} stroke={chartColors.grid} />
        <XAxis
          dataKey="period"
          tickFormatter={formatPeriodShort}
          tick={{ fill: chartColors.axis, fontSize: 12 }}
          axisLine={{ stroke: chartColors.grid }}
          tickLine={false}
          minTickGap={12}
        />
        <YAxis
          tickFormatter={(v) => formatNumber(v, { compact: true })}
          tick={{ fill: chartColors.axis, fontSize: 12 }}
          axisLine={false}
          tickLine={false}
          width={56}
        />
        <Tooltip
          cursor={type === 'bar' ? { fill: 'rgba(31,95,214,0.06)' } : { stroke: chartColors.axis, strokeDasharray: '3 3' }}
          content={({ active, payload, label }) =>
            active && payload?.length ? (
              <ChartTooltip
                title={formatPeriod(label)}
                rows={[
                  { label: 'Sales', value: formatCurrency(payload[0].payload.value, currency) },
                  { label: 'Transactions', value: formatNumber(payload[0].payload.transactions) },
                ]}
              />
            ) : null
          }
        />
        {type === 'bar' ? (
          <Bar dataKey="value" fill={chartColors.series1} radius={[4, 4, 0, 0]} maxBarSize={36} isAnimationActive={false} />
        ) : (
          <Line
            dataKey="value"
            stroke={chartColors.series1}
            strokeWidth={2}
            dot={{ r: 3, fill: chartColors.series1, strokeWidth: 0 }}
            activeDot={{ r: 5, stroke: '#fff', strokeWidth: 2 }}
            isAnimationActive={false}
          />
        )}
      </ComposedChart>
    </ResponsiveContainer>
  );
}
