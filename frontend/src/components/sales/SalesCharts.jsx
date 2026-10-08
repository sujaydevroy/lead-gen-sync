'use client';

import { useDispatch } from 'react-redux';
import Grid from '@mui/material/Grid';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import BarChartRoundedIcon from '@mui/icons-material/BarChartRounded';
import ShowChartRoundedIcon from '@mui/icons-material/ShowChartRounded';
import SectionCard from '@/components/ui/SectionCard';
import StatCard from '@/components/ui/StatCard';
import MonthlySalesChart from '@/components/charts/MonthlySalesChart';
import RankedBarChart from '@/components/charts/RankedBarChart';
import { setChartConfig } from '@/store/salesSlice';
import { formatCurrency, formatNumber, formatPeriod } from '@/lib/format';

/** Charts for the Upload Sales page, rendered from the chart data stored in Redux. */
export default function SalesCharts({ chartData, currency, monthlyChart }) {
  const dispatch = useDispatch();
  const { monthly, products, countries, dealers, total, transactions, dealerCount, productCount } = chartData;
  const range = monthly.length ? `${formatPeriod(monthly[0].period)} – ${formatPeriod(monthly[monthly.length - 1].period)}` : '—';

  return (
    <Grid container spacing={2.5}>
      <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
        <StatCard label="Total sales" value={formatCurrency(total, currency, { compact: true })} caption={formatCurrency(total, currency)} />
      </Grid>
      <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
        <StatCard
          label="Transactions"
          value={formatNumber(transactions)}
          caption={`${dealerCount} customers · ${productCount} products · ${countries.length} countries`}
        />
      </Grid>
      <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
        <StatCard label="Average transaction" value={transactions ? formatCurrency(total / transactions, currency, { compact: true }) : '—'} />
      </Grid>
      <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
        <StatCard label="Period covered" value={`${monthly.length} months`} caption={range} />
      </Grid>

      <Grid size={12}>
        <SectionCard
          title="Monthly sales"
          subtitle={`Total per month in ${currency}`}
          actions={
            <ToggleButtonGroup
              size="small"
              exclusive
              value={monthlyChart}
              onChange={(_, v) => v && dispatch(setChartConfig({ monthlyChart: v }))}
              aria-label="Chart type"
            >
              <ToggleButton value="bar" aria-label="Bar chart">
                <BarChartRoundedIcon fontSize="small" />
              </ToggleButton>
              <ToggleButton value="line" aria-label="Line chart">
                <ShowChartRoundedIcon fontSize="small" />
              </ToggleButton>
            </ToggleButtonGroup>
          }
        >
          <MonthlySalesChart data={monthly} currency={currency} type={monthlyChart} />
        </SectionCard>
      </Grid>

      <Grid size={{ xs: 12, lg: 6 }}>
        <SectionCard title="Top products" subtitle={`By sales in ${currency} · % = share of total`}>
          <RankedBarChart data={products} currency={currency} nameLabel="Product" labelWidth={190} />
        </SectionCard>
      </Grid>
      <Grid size={{ xs: 12, lg: 6 }}>
        <SectionCard title="Top customers" subtitle={`By sales in ${currency} · % = share of total`}>
          <RankedBarChart data={dealers} currency={currency} nameLabel="Customer" labelWidth={190} />
        </SectionCard>
      </Grid>
      <Grid size={12}>
        <SectionCard title="Sales by country" subtitle={`By sales in ${currency} · % = share of total`}>
          <RankedBarChart data={countries} currency={currency} nameLabel="Country" labelWidth={160} />
        </SectionCard>
      </Grid>
    </Grid>
  );
}
