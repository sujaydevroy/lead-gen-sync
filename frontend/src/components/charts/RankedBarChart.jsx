'use client';

import { useMemo } from 'react';
import { chartColors } from '@/lib/theme';
import { formatCurrency, formatNumber } from '@/lib/format';
import EChart from './EChart';
import { baseOption, shadowPointer, tooltipHtml, valueAxis } from './chartOptions';

/**
 * Horizontal ranked bar chart (single series, sorted high → low).
 * @param {{ data: { name: string, value: number, share?: number, transactions?: number }[], currency: string,
 *           labelWidth?: number, nameLabel?: string }} props
 */
export default function RankedBarChart({ data, currency, labelWidth = 150, nameLabel = 'Item' }) {
  const height = Math.max(160, data.length * 36 + 40);

  const option = useMemo(
    () => ({
      ...baseOption({
        axisPointer: shadowPointer,
        formatter: (params) => {
          const row = data[params[0].dataIndex];
          return tooltipHtml(`${nameLabel}: ${row.name}`, [
            { label: 'Sales', value: formatCurrency(row.value, currency) },
            ...(row.share !== undefined ? [{ label: 'Share of total', value: `${row.share.toFixed(1)}%` }] : []),
            ...(row.transactions !== undefined ? [{ label: 'Transactions', value: formatNumber(row.transactions) }] : []),
          ]);
        },
      }),
      grid: { top: 4, right: 72, bottom: 4, left: 4, containLabel: true },
      xAxis: valueAxis,
      yAxis: {
        type: 'category',
        inverse: true, // first (largest) item on top
        data: data.map((d) => String(d.name)),
        axisLabel: { color: chartColors.text, fontSize: 12, width: labelWidth - 8, overflow: 'truncate', interval: 0 },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      series: [
        {
          type: 'bar',
          data: data.map((d) => d.value),
          itemStyle: { color: chartColors.series1, borderRadius: [0, 4, 4, 0] },
          barMaxWidth: 22,
          barCategoryGap: 8,
          label: {
            show: true,
            position: 'right',
            color: chartColors.axis,
            fontSize: 12,
            formatter: ({ dataIndex }) => {
              const share = data[dataIndex].share;
              return share === undefined || share === null ? '' : `${Number(share).toFixed(1)}%`;
            },
          },
        },
      ],
    }),
    [data, currency, labelWidth, nameLabel],
  );

  return <EChart option={option} height={height} ariaLabel={`${nameLabel} sales ranking in ${currency}`} />;
}
