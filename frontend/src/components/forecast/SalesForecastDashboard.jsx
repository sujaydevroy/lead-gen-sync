'use client';

import Link from 'next/link';
import { useDispatch, useSelector } from 'react-redux';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Paper from '@mui/material/Paper';
import Box from '@mui/material/Box';
import Alert from '@mui/material/Alert';
import AlertTitle from '@mui/material/AlertTitle';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import Skeleton from '@mui/material/Skeleton';
import Divider from '@mui/material/Divider';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import TableCell from '@mui/material/TableCell';
import Accordion from '@mui/material/Accordion';
import AccordionSummary from '@mui/material/AccordionSummary';
import AccordionDetails from '@mui/material/AccordionDetails';
import ExpandMoreRoundedIcon from '@mui/icons-material/ExpandMoreRounded';
import UploadFileRoundedIcon from '@mui/icons-material/UploadFileRounded';
import ScienceOutlinedIcon from '@mui/icons-material/ScienceOutlined';
import PageHeader from '@/components/ui/PageHeader';
import SectionCard from '@/components/ui/SectionCard';
import EmptyState from '@/components/ui/EmptyState';
import RankedBarChart from '@/components/charts/RankedBarChart';
import SalesFilterBar from '@/components/sales/SalesFilterBar';
import { useNotify } from '@/components/providers/NotificationProvider';
import useSalesAnalytics from '@/hooks/useSalesAnalytics';
import useExchangeRates from '@/hooks/useExchangeRates';
import { setForecastScenario, loadSampleSales, resetFilters } from '@/store/salesSlice';
import { SCENARIOS, FORECAST_HORIZON } from '@/lib/salesForecast';
import { formatCurrency, formatNumber, formatPercent, formatPeriod } from '@/lib/format';
import SalesForecastChart from './SalesForecastChart';
import ForecastScenarioSelector from './ForecastScenarioSelector';
import SalesKpiCards from './SalesKpiCards';
import DeclinersTable from './DeclinersTable';

export default function SalesForecastDashboard() {
  const dispatch = useDispatch();
  const notify = useNotify();
  const { status, error, fileMetadata } = useSelector((state) => state.sales);
  useExchangeRates();
  const analytics = useSalesAnalytics();
  const {
    hasData,
    rows,
    monthly,
    products,
    dealers,
    regions,
    kpis,
    currency,
    converted,
    excludedRows,
    unknownCurrencies,
    forecast,
    chartRows,
    total: forecastTotal,
    growth,
    scenario,
    dealerConcentration,
    productConcentration,
    decliningDealers,
    decliningProducts,
  } = analytics;

  const scenarioLabel = SCENARIOS[scenario].label;
  const isDemo = fileMetadata?.name?.includes('demo data');

  const header = (
    <PageHeader
      title="Sales Forecast & Analytics"
      subtitle="Historical performance and a 12-month forecast built from your uploaded sales data"
      actions={
        hasData && (
          <ForecastScenarioSelector value={scenario} onChange={(v) => dispatch(setForecastScenario(v))} disabled={forecast.status !== 'ok'} />
        )
      }
    />
  );

  if (status === 'processing') {
    return (
      <>
        {header}
        <Stack spacing={2} aria-busy="true" aria-label="Processing sales data">
          <Skeleton variant="rounded" height={64} />
          <Grid container spacing={2}>
            {Array.from({ length: 6 }).map((_, i) => (
              <Grid key={i} size={{ xs: 12, sm: 6, lg: 4, xl: 2 }}>
                <Skeleton variant="rounded" height={110} />
              </Grid>
            ))}
          </Grid>
          <Skeleton variant="rounded" height={420} />
        </Stack>
      </>
    );
  }

  if (!hasData) {
    return (
      <>
        {header}
        <Paper variant="outlined" sx={{ borderRadius: 3 }}>
          <EmptyState
            variant={status === 'error' ? 'error' : 'empty'}
            title={status === 'error' ? 'Sales data could not be loaded' : 'No sales data yet'}
            description={
              status === 'error'
                ? error
                : 'Revenue analytics and forecasting need dated transaction records with amounts. Upload your sales workbook on the Upload Sales page to get started.'
            }
          >
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mt: 2 }}>
              <Button component={Link} href="/sales" variant="contained" startIcon={<UploadFileRoundedIcon />}>
                Go to Upload Sales
              </Button>
              <Button
                variant="outlined"
                startIcon={<ScienceOutlinedIcon />}
                onClick={() =>
                  dispatch(loadSampleSales())
                    .unwrap()
                    .then(() => notify('Sample sales file loaded (demo data)', 'success'))
                    .catch((message) => notify(String(message), 'error'))
                }
              >
                Load sample file (demo data)
              </Button>
            </Stack>
          </EmptyState>
        </Paper>
      </>
    );
  }

  return (
    <>
      {header}

      <Stack spacing={2.5}>
        <Paper variant="outlined" sx={{ p: 2, borderRadius: 3 }}>
          <SalesFilterBar />
        </Paper>

        <Stack spacing={1}>
          {isDemo && (
            <Alert severity="info" variant="outlined">
              You are viewing <strong>demo data</strong> from the bundled sample workbook (sample_sales.xlsx). Upload your own file on
              the <Link href="/sales">Upload Sales</Link> page to analyse real sales.
            </Alert>
          )}
          {converted && (
            <Alert severity="info" variant="outlined">
              The data contains several currencies. Figures are converted to {currency} with indicative reference rates (editable
              under &quot;Exchange rates&quot;). Choose a single currency to analyse without conversion.
            </Alert>
          )}
          {excludedRows > 0 && (
            <Alert severity="warning">
              {excludedRows} row(s) in {unknownCurrencies.join(', ')} have no exchange rate and are excluded.
            </Alert>
          )}
          {fileMetadata?.skippedRows > 0 && (
            <Alert severity="warning">
              {fileMetadata.skippedRows} row(s) of {fileMetadata.name} were skipped during upload because they had missing amounts or
              dates. They are not included in any figure.
            </Alert>
          )}
        </Stack>

        {rows.length === 0 ? (
          <Paper variant="outlined" sx={{ borderRadius: 3 }}>
            <EmptyState
              title="No sales match the selected filters"
              description="Widen the date range or clear the dealer, product and region filters."
              actionLabel="Reset filters"
              onAction={() => dispatch(resetFilters())}
            />
          </Paper>
        ) : (
          <>
            <SalesKpiCards
              kpis={kpis}
              monthly={monthly}
              currency={currency}
              forecastTotal={forecastTotal}
              growth={growth}
              forecastStatus={forecast.status}
              scenarioLabel={scenarioLabel}
            />

            <SectionCard
              title="Sales Trend & 12-Month Forecast"
              subtitle={
                forecast.status === 'ok'
                  ? `${monthly.length} months of actual sales, then a ${FORECAST_HORIZON}-month forecast in ${currency}`
                  : `${monthly.length} month${monthly.length === 1 ? '' : 's'} of actual sales in ${currency}`
              }
            >
              {forecast.status !== 'ok' && (
                <Alert severity="warning" sx={{ mb: 2 }}>
                  <AlertTitle>Insufficient historical data</AlertTitle>
                  {forecast.reason}
                </Alert>
              )}
              <SalesForecastChart
                rows={chartRows}
                currency={currency}
                lastActualPeriod={monthly[monthly.length - 1]?.period}
                hasForecast={forecast.status === 'ok'}
                scenarioLabel={scenarioLabel}
              />
              {forecast.status === 'ok' && (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>
                  Method: {forecast.methodLabel}. Shaded area = 95% prediction interval; it widens with the horizon and with
                  month-to-month volatility (residual σ ≈ {formatCurrency(forecast.sigma, currency, { compact: true })}).
                  {forecast.points.some((p) => p.clampedAtZero) && ' Negative projections are shown as 0.'}
                </Typography>
              )}
            </SectionCard>

            <Grid container spacing={2.5}>
              <Grid size={{ xs: 12, lg: 6 }}>
                <SectionCard title="Top 10 Products by Sales" subtitle={`Sales in ${currency} · % = contribution to total`}>
                  <RankedBarChart data={products.slice(0, 10)} currency={currency} nameLabel="Product" labelWidth={190} />
                </SectionCard>
              </Grid>
              <Grid size={{ xs: 12, lg: 6 }}>
                <SectionCard title="Top 10 Dealers by Sales" subtitle={`Sales in ${currency} · % = contribution to total`}>
                  <RankedBarChart data={dealers.slice(0, 10)} currency={currency} nameLabel="Dealer" labelWidth={190} />
                </SectionCard>
              </Grid>
              {regions.length > 0 && (
                <Grid size={{ xs: 12, lg: 7 }}>
                  <SectionCard
                    title="Sales by Region"
                    subtitle={
                      regions.length > 1
                        ? `Strongest: ${regions[0].name} (${regions[0].share.toFixed(1)}%) · Weakest: ${regions[regions.length - 1].name} (${regions[regions.length - 1].share.toFixed(1)}%) · region = Country column`
                        : 'Region = Country column of the uploaded sheet'
                    }
                  >
                    <RankedBarChart data={regions} currency={currency} nameLabel="Region" labelWidth={150} />
                  </SectionCard>
                </Grid>
              )}
              <Grid size={{ xs: 12, lg: regions.length > 0 ? 5 : 12 }}>
                <GrowthCard kpis={kpis} currency={currency} dealerConcentration={dealerConcentration} productConcentration={productConcentration} />
              </Grid>
              <Grid size={{ xs: 12, md: 6, xl: 4 }}>
                <QuarterlyCard quarterly={kpis.quarterly} currency={currency} />
              </Grid>
              <Grid size={{ xs: 12, md: 6, xl: 4 }}>
                <SectionCard title="Declining dealers" subtitle="Sales fell between the two most recent equal periods">
                  <DeclinersTable result={decliningDealers} currency={currency} nameLabel="Dealer" />
                </SectionCard>
              </Grid>
              <Grid size={{ xs: 12, xl: 4 }}>
                <SectionCard title="Declining products" subtitle="Sales fell between the two most recent equal periods">
                  <DeclinersTable result={decliningProducts} currency={currency} nameLabel="Product" />
                </SectionCard>
              </Grid>
            </Grid>

            <MethodologyCard forecast={forecast} growth={growth} monthly={monthly} currency={currency} />
          </>
        )}
      </Stack>
    </>
  );
}

function MetricRow({ label, value, hint }) {
  return (
    <Stack direction="row" spacing={2} sx={{ justifyContent: 'space-between', py: 1 }}>
      <Box>
        <Typography variant="body2">{label}</Typography>
        {hint && <Typography variant="caption">{hint}</Typography>}
      </Box>
      <Typography variant="body2" sx={{ fontWeight: 600, fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' }}>
        {value}
      </Typography>
    </Stack>
  );
}

function GrowthCard({ kpis, currency, dealerConcentration, productConcentration }) {
  const { growth } = kpis;
  return (
    <SectionCard title="Growth & concentration">
      <Stack divider={<Divider flexItem />}>
        <MetricRow
          label="Month-over-month growth"
          hint={growth.latest && growth.previous ? `${formatPeriod(growth.latest.period)} vs ${formatPeriod(growth.previous.period)}` : 'Needs 2 months'}
          value={growth.mom === null ? '—' : formatPercent(growth.mom, { signed: true })}
        />
        <MetricRow
          label="Year-over-year growth"
          hint={growth.yearAgo ? `${formatPeriod(growth.latest.period)} vs ${formatPeriod(growth.yearAgo.period)}` : 'Needs 13 months of history'}
          value={growth.yoy === null ? '—' : formatPercent(growth.yoy, { signed: true })}
        />
        <MetricRow
          label="Trailing 12 months vs prior 12"
          hint={growth.trailing12 === null ? 'Needs 24 months of history' : undefined}
          value={growth.trailing12 === null ? '—' : formatPercent(growth.trailing12, { signed: true })}
        />
        <MetricRow
          label="Average transaction value"
          hint={`${formatNumber(kpis.transactions)} transactions`}
          value={kpis.averageTransactionValue === null ? '—' : formatCurrency(kpis.averageTransactionValue, currency)}
        />
        {dealerConcentration && (
          <MetricRow
            label={`Top ${dealerConcentration.topN} dealers' share`}
            hint={`Concentration: ${dealerConcentration.level} (HHI ${Math.round(dealerConcentration.hhi)})`}
            value={formatPercent(dealerConcentration.topShare)}
          />
        )}
        {productConcentration && (
          <MetricRow
            label={`Top ${productConcentration.topN} products' share`}
            hint={`Concentration: ${productConcentration.level} (HHI ${Math.round(productConcentration.hhi)})`}
            value={formatPercent(productConcentration.topShare)}
          />
        )}
      </Stack>
    </SectionCard>
  );
}

function QuarterlyCard({ quarterly, currency }) {
  return (
    <SectionCard title="Quarterly sales" subtitle="Partial quarters are marked">
      <Table size="small" aria-label="Quarterly sales">
        <TableHead>
          <TableRow>
            <TableCell>Quarter</TableCell>
            <TableCell align="right">Sales</TableCell>
            <TableCell align="right">QoQ</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {quarterly.map((q, i) => {
            const prev = quarterly[i - 1];
            const comparable = prev && prev.months === 3 && q.months === 3 && prev.value > 0;
            const change = comparable ? ((q.value - prev.value) / prev.value) * 100 : null;
            return (
              <TableRow key={q.quarter}>
                <TableCell>
                  {q.quarter.replace('-', ' ')}
                  {q.months < 3 && (
                    <Typography component="span" variant="caption">
                      {' '}
                      ({q.months} mo)
                    </Typography>
                  )}
                </TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: 'tabular-nums' }}>
                  {formatCurrency(q.value, currency, { compact: true })}
                </TableCell>
                <TableCell align="right" sx={{ color: change === null ? 'text.secondary' : change < 0 ? 'error.main' : 'success.main' }}>
                  {change === null ? '—' : formatPercent(change, { signed: true })}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </SectionCard>
  );
}

function MethodologyCard({ forecast, growth, monthly, currency }) {
  const params = forecast.status === 'ok' ? forecast.params : null;
  return (
    <Accordion variant="outlined" disableGutters sx={{ borderRadius: 3, '&:before': { display: 'none' } }}>
      <AccordionSummary expandIcon={<ExpandMoreRoundedIcon />}>
        <Typography variant="subtitle1">How these numbers are calculated</Typography>
      </AccordionSummary>
      <AccordionDetails>
        <Stack spacing={1.5}>
          <Typography variant="body2">
            <strong>Data source.</strong> Every figure comes from the workbook uploaded on Upload Sales (stored in the Redux sales
            workspace). Each row&apos;s Month + Year gives its period and its Amount the sales value. Months between the first and last
            sale with no rows count as zero sales. Dealer = CustomerName column, region = Country column.
          </Typography>
          <Typography variant="body2">
            <strong>Model choice.</strong> 24+ months → Holt-Winters additive with 12-month seasonality; 6–23 months → exponential
            smoothing, choosing between simple (level only), Holt linear-trend and Holt damped-trend by the lowest AICc, so a trend is
            only used when the data supports it; 3–5 months → least-squares linear trend; fewer than 3 months with sales, or fewer
            than half the months with sales → no forecast. Smoothing parameters are picked by grid search to minimise
            one-step-ahead squared error.
            {forecast.status === 'ok' && (
              <>
                {' '}
                Current model: <em>{forecast.methodLabel}</em> fitted on {monthly.length} months
                {params && 'alpha' in params &&
                  ` (α = ${params.alpha}${'beta' in params ? `, β = ${params.beta}` : ''}${'phi' in params ? `, φ = ${params.phi}` : ''}${'gamma' in params ? `, γ = ${params.gamma}` : ''})`}
                .
              </>
            )}
          </Typography>
          <Typography variant="body2">
            <strong>Confidence bounds.</strong> σ is the standard deviation of the model&apos;s in-sample one-step-ahead errors. The
            h-month-ahead standard error grows with the smoothing weights (σ·√(1 + Σ cⱼ²)); the bounds are forecast ± 1.96 × that
            error (95%; Student-t for the linear-trend model), floored at 0 because sales cannot be negative.
          </Typography>
          <Typography variant="body2">
            <strong>Scenarios.</strong> Base = point forecast. For Conservative / Optimistic, 2,000 future 12-month paths are
            simulated from the fitted model (normally distributed errors with the model&apos;s residual σ, monthly sales floored at
            0). The 16th and 84th percentiles of the simulated 12-month totals (≈ one standard deviation either side) set the
            scenario totals, and each scenario keeps the base forecast&apos;s monthly shape. The percentages come from the model&apos;s
            own uncertainty, not from fixed ±% assumptions.
            {forecast.status === 'ok' && forecast.scenarioTotals && (
              <>
                {' '}
                Current 12-month totals: conservative {formatCurrency(forecast.scenarioTotals.conservative, currency, { compact: true })},
                base {formatCurrency(forecast.scenarioTotals.base, currency, { compact: true })}, optimistic{' '}
                {formatCurrency(forecast.scenarioTotals.optimistic, currency, { compact: true })}.
              </>
            )}
          </Typography>
          <Typography variant="body2">
            <strong>Forecast growth.</strong> (forecast 12-month total − comparable historical sales) ÷ comparable historical sales ×
            100, where comparable = {growth?.basis || 'the last 12 months of actual sales (or the annualised average when less history exists)'}.
          </Typography>
          <Typography variant="body2">
            <strong>Filters.</strong> Currency, date range, dealer, product and region filters apply to every KPI, chart, table and to
            the forecast itself (the model is refitted on the filtered monthly series).
          </Typography>
        </Stack>
      </AccordionDetails>
    </Accordion>
  );
}
