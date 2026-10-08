'use client';

import { useMemo } from 'react';
import { chartColors } from '@/lib/theme';
import { formatCurrency, formatNumber, formatPeriod, formatPeriodShort } from '@/lib/format';
import EChart from './EChart';
import { baseOption, linePointer, shadowPointer, tooltipHtml, valueAxis } from './chartOptions';

/** Monthly sales totals as bars or a line. data = [{ period: 'YYYY-MM', value, transactions }] */
export default function MonthlySalesChart({ data, currency, type = 'bar', height = 300 }) {
  const option = useMemo(
    () => ({
      ...baseOption({
        axisPointer: type === 'bar' ? shadowPointer : linePointer,
        formatter: (params) => {
          const row = data[params[0].dataIndex];
          return tooltipHtml(formatPeriod(row.period), [
            { label: 'Sales', value: formatCurrency(row.value, currency) },
            { label: 'Transactions', value: formatNumber(row.transactions) },
          ]);
        },
      }),
      grid: { top: 12, right: 12, bottom: 8, left: 4, containLabel: true },
      xAxis: {
        type: 'category',
        data: data.map((d) => d.period),
        boundaryGap: type === 'bar',
        axisLabel: { color: chartColors.axis, fontSize: 12, formatter: formatPeriodShort, hideOverlap: true },
        axisLine: { lineStyle: { color: chartColors.grid } },
        axisTick: { show: false },
      },
      yAxis: valueAxis,
      series: [
        type === 'bar'
          ? {
              type: 'bar',
              data: data.map((d) => d.value),
              itemStyle: { color: chartColors.series1, borderRadius: [4, 4, 0, 0] },
              barMaxWidth: 36,
            }
          : {
              type: 'line',
              data: data.map((d) => d.value),
              lineStyle: { color: chartColors.series1, width: 2 },
              itemStyle: { color: chartColors.series1 },
              symbol: 'circle',
              symbolSize: 6,
              emphasis: { scale: 1.6, itemStyle: { borderColor: '#fff', borderWidth: 2 } },
            },
      ],
    }),
    [data, currency, type],
  );

  return <EChart option={option} height={height} ariaLabel={`Monthly sales in ${currency}`} />;
}
