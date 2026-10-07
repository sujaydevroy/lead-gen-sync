'use client';

import Grid from '@mui/material/Grid';
import PaidOutlinedIcon from '@mui/icons-material/PaidOutlined';
import InsightsRoundedIcon from '@mui/icons-material/InsightsRounded';
import TrendingUpRoundedIcon from '@mui/icons-material/TrendingUpRounded';
import TrendingDownRoundedIcon from '@mui/icons-material/TrendingDownRounded';
import CalendarMonthOutlinedIcon from '@mui/icons-material/CalendarMonthOutlined';
import Inventory2OutlinedIcon from '@mui/icons-material/Inventory2Outlined';
import StorefrontOutlinedIcon from '@mui/icons-material/StorefrontOutlined';
import StatCard from '@/components/ui/StatCard';
import { formatCurrency, formatPercent, formatPeriod } from '@/lib/format';

/** Six headline KPIs. Missing values render as "—" with an explanation, never as 0. */
export default function SalesKpiCards({ kpis, monthly, currency, forecastTotal, growth, forecastStatus, scenarioLabel }) {
  const range = monthly.length ? `${formatPeriod(monthly[0].period)} – ${formatPeriod(monthly[monthly.length - 1].period)}` : '';
  const forecastOk = forecastStatus === 'ok';
  const growthValue = forecastOk ? growth?.growth : null;

  const cards = [
    {
      label: 'Total Historical Sales',
      value: formatCurrency(kpis.totalSales, currency, { compact: true }),
      caption: `${formatCurrency(kpis.totalSales, currency)} · ${range}`,
      Icon: PaidOutlinedIcon,
    },
    {
      label: 'Forecasted Next 12 Months',
      value: forecastOk ? formatCurrency(forecastTotal, currency, { compact: true }) : '—',
      caption: forecastOk ? `${scenarioLabel} scenario` : 'Insufficient historical data',
      Icon: InsightsRoundedIcon,
    },
    {
      label: 'Forecast Growth',
      value: growthValue === null || growthValue === undefined ? '—' : formatPercent(growthValue, { signed: true }),
      caption: forecastOk ? (growth?.growth === null ? 'No comparable sales' : `vs ${growth.basis}`) : 'Requires a forecast',
      Icon: growthValue !== null && growthValue < 0 ? TrendingDownRoundedIcon : TrendingUpRoundedIcon,
      tooltip: '((Forecasted 12-month sales − comparable historical sales) ÷ comparable historical sales) × 100',
    },
    {
      label: 'Average Monthly Sales',
      value: kpis.averageMonthlySales === null ? '—' : formatCurrency(kpis.averageMonthlySales, currency, { compact: true }),
      caption: `Over ${kpis.months} month${kpis.months === 1 ? '' : 's'} (incl. months without sales)`,
      Icon: CalendarMonthOutlinedIcon,
    },
    {
      label: 'Top Product',
      value: kpis.topProduct?.name || '—',
      caption: kpis.topProduct ? `${formatCurrency(kpis.topProduct.value, currency, { compact: true })} · ${kpis.topProduct.share.toFixed(1)}% of sales` : '',
      Icon: Inventory2OutlinedIcon,
      tooltip: kpis.topProduct?.name,
    },
    {
      label: 'Top Dealer',
      value: kpis.topDealer?.name || '—',
      caption: kpis.topDealer ? `${formatCurrency(kpis.topDealer.value, currency, { compact: true })} · ${kpis.topDealer.share.toFixed(1)}% of sales` : '',
      Icon: StorefrontOutlinedIcon,
      tooltip: kpis.topDealer?.name,
    },
  ];

  return (
    <Grid container spacing={2}>
      {cards.map(({ label, value, caption, Icon, tooltip }) => (
        <Grid key={label} size={{ xs: 12, sm: 6, lg: 4, xl: 2 }}>
          <StatCard label={label} value={value} caption={caption} icon={<Icon fontSize="small" />} tooltip={tooltip} />
        </Grid>
      ))}
    </Grid>
  );
}
