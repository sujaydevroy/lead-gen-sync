'use client';

import { useMemo, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import MenuItem from '@mui/material/MenuItem';
import Autocomplete from '@mui/material/Autocomplete';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import CurrencyExchangeRoundedIcon from '@mui/icons-material/CurrencyExchangeRounded';
import RestartAltRoundedIcon from '@mui/icons-material/RestartAltRounded';
import { setFilters, resetFilters } from '@/store/salesSlice';
import { getSalesOptions, addMonths, monthsBetween } from '@/lib/salesAnalytics';
import { formatPeriod } from '@/lib/format';
import { ALL_CURRENCIES, createDefaultSalesFilters } from '@/types/sales';
import FxRatesDialog from './FxRatesDialog';

/**
 * Filters shared by Upload Sales and Sales Forecast (state lives in Redux `sales.filters`).
 * @param {{ show?: { dealers?: boolean, products?: boolean, regions?: boolean, dates?: boolean } }} props
 */
export default function SalesFilterBar({ show = { dates: true, dealers: true, products: true, regions: true } }) {
  const dispatch = useDispatch();
  const { processedData, filters, chartConfig } = useSelector((state) => state.sales);
  const [fxOpen, setFxOpen] = useState(false);

  const options = useMemo(() => getSalesOptions(processedData), [processedData]);
  const periods = useMemo(() => {
    if (!options.firstPeriod) return [];
    const span = monthsBetween(options.firstPeriod, options.lastPeriod);
    return Array.from({ length: span + 1 }, (_, i) => addMonths(options.firstPeriod, i));
  }, [options.firstPeriod, options.lastPeriod]);

  const set = (patch) => dispatch(setFilters(patch));
  const isDefault = JSON.stringify(filters) === JSON.stringify(createDefaultSalesFilters());
  const reportingOptions = Object.keys(chartConfig.fxRates);

  const multi = (key, label, values) => (
    <Autocomplete
      multiple
      size="small"
      limitTags={1}
      options={values}
      value={filters[key]}
      onChange={(_, v) => set({ [key]: v })}
      renderValue={(selected, getItemProps) =>
        selected.map((option, index) => {
          const { key: itemKey, ...itemProps } = getItemProps({ index });
          return <Chip key={itemKey} size="small" label={option} {...itemProps} />;
        })
      }
      renderInput={(params) => <TextField {...params} label={label} placeholder={filters[key].length ? '' : 'All'} />}
    />
  );

  return (
    <>
      <Grid container spacing={1.5} sx={{ alignItems: 'center' }}>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 2 }}>
          <TextField
            select
            size="small"
            fullWidth
            label="Currency"
            value={filters.currency}
            onChange={(e) => set({ currency: e.target.value })}
          >
            <MenuItem value={ALL_CURRENCIES}>All currencies (converted)</MenuItem>
            {options.currencies.map((c) => (
              <MenuItem key={c} value={c}>
                {c} only
              </MenuItem>
            ))}
          </TextField>
        </Grid>
        {filters.currency === ALL_CURRENCIES && (
          <Grid size={{ xs: 12, sm: 6, md: 4, lg: 2 }}>
            <TextField
              select
              size="small"
              fullWidth
              label="Report in"
              value={filters.reportingCurrency}
              onChange={(e) => set({ reportingCurrency: e.target.value })}
            >
              {reportingOptions.map((c) => (
                <MenuItem key={c} value={c}>
                  {c}
                </MenuItem>
              ))}
            </TextField>
          </Grid>
        )}
        {show.dates && (
          <>
            <Grid size={{ xs: 6, md: 4, lg: 2 }}>
              <TextField select size="small" fullWidth label="From" value={filters.dateFrom} onChange={(e) => set({ dateFrom: e.target.value })}>
                <MenuItem value="">Earliest</MenuItem>
                {periods
                  .filter((p) => !filters.dateTo || p <= filters.dateTo)
                  .map((p) => (
                    <MenuItem key={p} value={p}>
                      {formatPeriod(p)}
                    </MenuItem>
                  ))}
              </TextField>
            </Grid>
            <Grid size={{ xs: 6, md: 4, lg: 2 }}>
              <TextField select size="small" fullWidth label="To" value={filters.dateTo} onChange={(e) => set({ dateTo: e.target.value })}>
                <MenuItem value="">Latest</MenuItem>
                {periods
                  .filter((p) => !filters.dateFrom || p >= filters.dateFrom)
                  .map((p) => (
                    <MenuItem key={p} value={p}>
                      {formatPeriod(p)}
                    </MenuItem>
                  ))}
              </TextField>
            </Grid>
          </>
        )}
        {show.dealers && <Grid size={{ xs: 12, sm: 6, md: 4, lg: 2 }}>{multi('customers', 'Dealer / customer', options.customers)}</Grid>}
        {show.products && <Grid size={{ xs: 12, sm: 6, md: 4, lg: 2 }}>{multi('products', 'Product', options.products)}</Grid>}
        {show.regions && <Grid size={{ xs: 12, sm: 6, md: 4, lg: 2 }}>{multi('countries', 'Region (country)', options.countries)}</Grid>}
        <Grid size={{ xs: 12, md: 'auto' }}>
          <Stack direction="row" spacing={1}>
            {filters.currency === ALL_CURRENCIES && (
              <Button size="small" startIcon={<CurrencyExchangeRoundedIcon />} onClick={() => setFxOpen(true)}>
                Exchange rates
              </Button>
            )}
            <Button size="small" color="inherit" startIcon={<RestartAltRoundedIcon />} disabled={isDefault} onClick={() => dispatch(resetFilters())}>
              Reset filters
            </Button>
          </Stack>
        </Grid>
      </Grid>
      <FxRatesDialog open={fxOpen} onClose={() => setFxOpen(false)} currencies={options.currencies} />
    </>
  );
}
