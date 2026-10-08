'use client';

import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, LabelList } from 'recharts';
import { chartColors } from '@/lib/theme';
import { formatCurrency, formatNumber } from '@/lib/format';
import ChartTooltip from './ChartTooltip';

const truncate = (text, max) => (text.length > max ? `${text.slice(0, max - 1)}…` : text);

/**
 * Horizontal ranked bar chart (single series, sorted high → low).
 * @param {{ data: { name: string, value: number, share?: number, transactions?: number }[], currency: string,
 *           labelWidth?: number, nameLabel?: string }} props
 */
export default function RankedBarChart({ data, currency, labelWidth = 150, nameLabel = 'Item' }) {
  const height = Math.max(160, data.length * 36 + 40);
  const maxChars = Math.floor(labelWidth / 7);

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 72, bottom: 4, left: 4 }} barCategoryGap={8}>
        <CartesianGrid horizontal={false} stroke={chartColors.grid} />
        <XAxis
          type="number"
          tickFormatter={(v) => formatNumber(v, { compact: true })}
          tick={{ fill: chartColors.axis, fontSize: 12 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="name"
          width={labelWidth}
          tick={{ fill: chartColors.text, fontSize: 12 }}
          tickFormatter={(v) => truncate(String(v), maxChars)}
          axisLine={false}
          tickLine={false}
          interval={0}
        />
        <Tooltip
          cursor={{ fill: 'rgba(31,95,214,0.06)' }}
          content={({ active, payload }) =>
            active && payload?.length ? (
              <ChartTooltip
                title={`${nameLabel}: ${payload[0].payload.name}`}
                rows={[
                  { label: 'Sales', value: formatCurrency(payload[0].payload.value, currency) },
                  ...(payload[0].payload.share !== undefined
                    ? [{ label: 'Share of total', value: `${payload[0].payload.share.toFixed(1)}%` }]
                    : []),
                  ...(payload[0].payload.transactions !== undefined
                    ? [{ label: 'Transactions', value: formatNumber(payload[0].payload.transactions) }]
                    : []),
                ]}
              />
            ) : null
          }
        />
        <Bar dataKey="value" fill={chartColors.series1} radius={[0, 4, 4, 0]} maxBarSize={22} isAnimationActive={false}>
          <LabelList
            dataKey="share"
            position="right"
            formatter={(v) => (v === undefined || v === null ? '' : `${Number(v).toFixed(1)}%`)}
            style={{ fill: chartColors.axis, fontSize: 12 }}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
