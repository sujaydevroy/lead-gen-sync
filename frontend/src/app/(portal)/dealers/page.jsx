'use client';

import { useCallback, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Grid from '@mui/material/Grid';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Badge from '@mui/material/Badge';
import Drawer from '@mui/material/Drawer';
import Typography from '@mui/material/Typography';
import LinearProgress from '@mui/material/LinearProgress';
import useMediaQuery from '@mui/material/useMediaQuery';
import { useTheme } from '@mui/material/styles';
import RefreshRoundedIcon from '@mui/icons-material/RefreshRounded';
import TuneRoundedIcon from '@mui/icons-material/TuneRounded';
import PageHeader from '@/components/ui/PageHeader';
import EmptyState from '@/components/ui/EmptyState';
import DealerFilterPanel from '@/components/filters/DealerFilterPanel';
import DealerSearchField from '@/components/dealers/DealerSearchField';
import ActiveFilterChips from '@/components/dealers/ActiveFilterChips';
import DealerTable, { DealerTableSkeleton } from '@/components/dealers/DealerTable';
import DealerCard, { DealerCardSkeleton } from '@/components/dealers/DealerCard';
import DealerPagination from '@/components/dealers/DealerPagination';
import ContactDealerDialog from '@/components/communication/ContactDealerDialog';
import useDealerList from '@/hooks/useDealerList';
import useCompanySector from '@/hooks/useCompanySector';
import {
  setSearch,
  setFilters,
  removeFilterValue,
  clearFilters,
  clearFilterGroups,
  setPage,
  setPageSize,
} from '@/store/dealerListSlice';

const SIDEBAR_WIDTH = { md: 248, lg: 280 };

export default function DealersPage() {
  const dispatch = useDispatch();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const { applyFiltersInstantly, desktopDealerView } = useSelector((state) => state.settings);
  const companySector = useCompanySector();
  const { data, loading, error, reload, search, filters, page, pageSize } = useDealerList();

  const [filtersOpen, setFiltersOpen] = useState(false);
  const [contactDealer, setContactDealer] = useState(null);

  const facets = data?.facets || null;
  const activeFilterCount = Object.values(filters).reduce((n, list) => n + list.length, 0);
  const hasCriteria = activeFilterCount > 0 || Boolean(search);
  const showCards = isMobile || desktopDealerView === 'cards';

  const onSearch = useCallback((value) => dispatch(setSearch(value)), [dispatch]);
  const onApply = useCallback((next) => dispatch(setFilters(next)), [dispatch]);
  const onClearAll = useCallback(() => dispatch(clearFilterGroups()), [dispatch]);
  const onClearEverything = useCallback(() => dispatch(clearFilters()), [dispatch]);

  const filterPanel = (inDrawer) => (
    <DealerFilterPanel
      facets={facets}
      applied={filters}
      onApply={onApply}
      onClearAll={onClearAll}
      // In the mobile drawer, edits are applied with the button so the list doesn't jump behind it.
      instant={inDrawer ? false : applyFiltersInstantly}
      companySector={companySector}
      onDone={inDrawer ? () => setFiltersOpen(false) : undefined}
    />
  );

  let content;
  if (error) {
    content = (
      <EmptyState
        variant="error"
        title="Unable to load dealers."
        description={`Please try again. ${error.message ? `(${error.message})` : ''}`}
        actionLabel="Retry"
        onAction={reload}
      />
    );
  } else if (loading && !data?.items) {
    content = showCards ? <CardGridSkeleton /> : <DealerTableSkeleton rows={Math.min(pageSize, 10)} />;
  } else if (loading) {
    content = showCards ? <CardGridSkeleton /> : <DealerTableSkeleton rows={Math.min(pageSize, data.items.length || 8)} />;
  } else if (!data.items.length) {
    content = (
      <EmptyState
        title="No dealers found"
        description="Try changing your country, region or search filters."
        actionLabel="Clear Filters"
        onAction={onClearEverything}
      />
    );
  } else if (showCards) {
    content = (
      <Grid container spacing={2} sx={{ p: { xs: 0, md: 2 } }}>
        {data.items.map((dealer) => (
          <Grid key={dealer.dealer_id} size={{ xs: 12, sm: 6, xl: 4 }}>
            <DealerCard dealer={dealer} onContact={setContactDealer} />
          </Grid>
        ))}
      </Grid>
    );
  } else {
    content = <DealerTable dealers={data.items} onContact={setContactDealer} />;
  }

  const total = data?.total ?? 0;

  return (
    <>
      <PageHeader
        title="Dealers"
        subtitle="Find and communicate with your dealers"
        meta={
          data && (
            <Chip
              size="small"
              color="primary"
              variant="outlined"
              label={`${data.totalDealers} total dealers`}
              sx={{ fontWeight: 600 }}
            />
          )
        }
        actions={
          <Button variant="outlined" startIcon={<RefreshRoundedIcon />} onClick={reload} disabled={loading}>
            Refresh
          </Button>
        }
      />

      <Stack direction="row" spacing={3} sx={{ alignItems: 'flex-start' }}>
        {/* Desktop / tablet: filters are always visible on the left. */}
        <Paper
          variant="outlined"
          component="aside"
          aria-label="Dealer filters"
          sx={{
            // A flex column with a max height: the filter list scrolls inside, the buttons stay visible.
            display: { xs: 'none', md: 'flex' },
            flexDirection: 'column',
            width: SIDEBAR_WIDTH,
            flexShrink: 0,
            position: 'sticky',
            top: 132,
            maxHeight: 'calc(100vh - 152px)',
            overflow: 'hidden',
            borderRadius: 3,
          }}
        >
          {filterPanel(false)}
        </Paper>

        <Box sx={{ flexGrow: 1, minWidth: 0 }}>
          <Stack direction="row" spacing={1.5} sx={{ mb: 2 }}>
            <DealerSearchField value={search} onSearch={onSearch} />
            <Badge badgeContent={activeFilterCount} color="primary" sx={{ display: { xs: 'inline-flex', md: 'none' } }}>
              <Button variant="outlined" startIcon={<TuneRoundedIcon />} onClick={() => setFiltersOpen(true)} sx={{ bgcolor: 'background.paper' }}>
                Filters
              </Button>
            </Badge>
          </Stack>

          <Stack spacing={1.5} sx={{ mb: 2 }}>
            <Typography variant="subtitle1" component="p" aria-live="polite">
              {data ? `${total} dealer${total === 1 ? '' : 's'} found` : 'Loading dealers…'}
              {data && hasCriteria && (
                <Typography component="span" variant="body2" color="text.secondary">
                  {' '}
                  of {data.totalDealers}
                </Typography>
              )}
            </Typography>
            <ActiveFilterChips
              filters={filters}
              search={search}
              onRemove={(group, value) => dispatch(removeFilterValue({ group, value }))}
              onClearSearch={() => dispatch(setSearch(''))}
              onClearAll={onClearEverything}
            />
          </Stack>

          <Paper variant="outlined" sx={{ borderRadius: 3, overflow: 'hidden', ...(showCards && isMobile ? { border: 0, bgcolor: 'transparent' } : {}) }}>
            {loading && data && <LinearProgress sx={{ height: 2 }} aria-label="Refreshing dealers" />}
            {content}
            {!error && data && data.items.length > 0 && (
              <Box sx={{ borderTop: showCards && isMobile ? 0 : 1, borderColor: 'divider' }}>
                <DealerPagination
                  page={data.page}
                  pageSize={pageSize}
                  total={total}
                  totalPages={data.totalPages}
                  onPageChange={(p) => {
                    dispatch(setPage(p));
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                  }}
                  onPageSizeChange={(size) => dispatch(setPageSize(size))}
                />
              </Box>
            )}
          </Paper>
        </Box>
      </Stack>

      {/* Mobile: filters slide out from the left. */}
      <Drawer
        anchor="left"
        open={filtersOpen && isMobile}
        onClose={() => setFiltersOpen(false)}
        slotProps={{ paper: { sx: { width: { xs: '88vw', sm: 340 } } } }}
      >
        {filterPanel(true)}
      </Drawer>

      <ContactDealerDialog dealer={contactDealer} open={Boolean(contactDealer)} onClose={() => setContactDealer(null)} />
    </>
  );
}

function CardGridSkeleton() {
  return (
    <Grid container spacing={2} sx={{ p: { xs: 0, md: 2 } }} aria-busy="true" aria-label="Loading dealers">
      {Array.from({ length: 6 }).map((_, i) => (
        <Grid key={i} size={{ xs: 12, sm: 6, xl: 4 }}>
          <DealerCardSkeleton />
        </Grid>
      ))}
    </Grid>
  );
}
