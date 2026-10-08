'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useDispatch, useSelector } from 'react-redux';
import Stack from '@mui/material/Stack';
import Paper from '@mui/material/Paper';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';
import Skeleton from '@mui/material/Skeleton';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogActions from '@mui/material/DialogActions';
import InsightsRoundedIcon from '@mui/icons-material/InsightsRounded';
import PageHeader from '@/components/ui/PageHeader';
import SectionCard from '@/components/ui/SectionCard';
import EmptyState from '@/components/ui/EmptyState';
import SalesUploadZone from '@/components/sales/SalesUploadZone';
import SalesFileSummary from '@/components/sales/SalesFileSummary';
import SalesFilterBar from '@/components/sales/SalesFilterBar';
import SalesCharts from '@/components/sales/SalesCharts';
import SalesRecordsTable from '@/components/sales/SalesRecordsTable';
import SalesJsonView from '@/components/sales/SalesJsonView';
import { useNotify } from '@/components/providers/NotificationProvider';
import RecentUploads from '@/components/sales/RecentUploads';
import useAsync from '@/hooks/useAsync';
import useExchangeRates from '@/hooks/useExchangeRates';
import salesService from '@/services/salesService';
import {
  uploadSalesFile,
  loadSampleSales,
  openSalesUpload,
  clearSalesData,
  setChartData,
  setChartConfig,
} from '@/store/salesSlice';
import { applySalesFilters, buildSalesChartData } from '@/lib/salesAnalytics';

export default function UploadSalesPage() {
  const dispatch = useDispatch();
  const notify = useNotify();
  const { status, error, uploadId, processedData, fileMetadata, filters, chartConfig, chartData, chartDataKey } = useSelector(
    (state) => state.sales,
  );
  const [confirmClear, setConfirmClear] = useState(false);
  const uploads = useAsync(() => salesService.listUploads(), []);
  useExchangeRates();

  const hasData = processedData.length > 0;
  const processing = status === 'processing';

  // Filtering is cheap; chart generation is cached in Redux by the inputs it was built from,
  // so returning to this page re-uses the stored charts instead of regenerating them.
  const filtered = useMemo(() => applySalesFilters(processedData, filters, chartConfig.fxRates), [processedData, filters, chartConfig.fxRates]);
  const chartKey = useMemo(
    () => JSON.stringify([fileMetadata?.uploadedAt, filters, chartConfig.fxRates]),
    [fileMetadata?.uploadedAt, filters, chartConfig.fxRates],
  );

  useEffect(() => {
    if (hasData && chartKey !== chartDataKey) {
      dispatch(setChartData({ key: chartKey, data: buildSalesChartData(filtered.rows) }));
    }
  }, [hasData, chartKey, chartDataKey, filtered.rows, dispatch]);

  const run = async (action, label) => {
    try {
      const result = await dispatch(action).unwrap();
      notify(`${label}: ${result.fileMetadata.validRows} records`, 'success');
      uploads.reload();
    } catch (message) {
      notify(typeof message === 'string' ? message : 'The file could not be processed.', 'error');
    }
  };

  const onFile = (file) => run(uploadSalesFile(file), `${file.name} converted to JSON`);
  const onSample = () => run(loadSampleSales(), 'Sample file loaded');
  const onOpen = (id) => run(openSalesUpload(id), 'Upload opened');
  const onDeleted = (id) => {
    if (id === uploadId) dispatch(clearSalesData());
    uploads.reload();
  };

  const recentUploads = (
    <RecentUploads
      uploads={uploads.data}
      loading={uploads.loading}
      error={uploads.error}
      onReload={uploads.reload}
      currentUploadId={uploadId}
      onOpen={onOpen}
      onDeleted={onDeleted}
      opening={processing}
    />
  );

  const chartsReady = chartData && chartDataKey === chartKey;

  return (
    <>
      <PageHeader
        title="Upload Sales"
        subtitle="Upload an Excel sales workbook, convert it to JSON and explore it with charts and search"
        actions={
          hasData && (
            <Button component={Link} href="/forecast" variant="contained" startIcon={<InsightsRoundedIcon />}>
              Open Sales Forecast
            </Button>
          )
        }
      />

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
          {hasData ? ' The previously uploaded data is still shown.' : ''}
        </Alert>
      )}

      {!hasData ? (
        <Stack spacing={2.5}>
          <SalesUploadZone onFile={onFile} onSample={onSample} processing={processing} />
          {recentUploads}
        </Stack>
      ) : (
        <Stack spacing={2.5}>
          <SectionCard>
            <SalesFileSummary metadata={fileMetadata} onClear={() => setConfirmClear(true)} />
            <Stack sx={{ mt: 2 }}>
              <SalesUploadZone onFile={onFile} processing={processing} compact />
            </Stack>
          </SectionCard>

          <Paper variant="outlined" sx={{ p: 2, borderRadius: 3 }}>
            <SalesFilterBar />
          </Paper>

          {filtered.excludedRows > 0 && (
            <Alert severity="warning">
              {filtered.excludedRows} row(s) in {filtered.unknownCurrencies.join(', ')} have no exchange rate and are excluded from the converted totals.
              Add a rate under &quot;Exchange rates&quot; or pick a single currency.
            </Alert>
          )}
          {filtered.converted && (
            <Alert severity="info" variant="outlined">
              Amounts in different currencies are converted to {filtered.currency} with indicative reference rates. Select a single
              currency to see unconverted figures.
            </Alert>
          )}

          <Paper variant="outlined" sx={{ borderRadius: 3, overflow: 'hidden' }}>
            <Tabs
              value={chartConfig.activeView}
              onChange={(_, v) => dispatch(setChartConfig({ activeView: v }))}
              sx={{ px: 2, borderBottom: 1, borderColor: 'divider' }}
            >
              <Tab value="charts" label="Charts" />
              <Tab value="table" label={`Records (${filtered.rows.length})`} />
              <Tab value="json" label="JSON" />
            </Tabs>

            {chartConfig.activeView === 'charts' &&
              (filtered.rows.length === 0 ? (
                <EmptyState title="No sales match these filters" description="Change the currency, date range or other filters." />
              ) : chartsReady ? (
                <Stack sx={{ p: { xs: 1.5, md: 2.5 }, bgcolor: 'background.default' }}>
                  <SalesCharts chartData={chartData} currency={filtered.currency} monthlyChart={chartConfig.monthlyChart} />
                </Stack>
              ) : (
                <Stack spacing={2} sx={{ p: 2.5 }}>
                  <Skeleton variant="rounded" height={90} />
                  <Skeleton variant="rounded" height={300} />
                </Stack>
              ))}
            {chartConfig.activeView === 'table' && (
              <SalesRecordsTable rows={filtered.rows} reportingCurrency={filtered.currency} converted={filtered.converted} />
            )}
            {chartConfig.activeView === 'json' && <SalesJsonView records={processedData} fileName={fileMetadata?.name} />}
          </Paper>
          {recentUploads}
        </Stack>
      )}

      <Dialog open={confirmClear} onClose={() => setConfirmClear(false)}>
        <DialogTitle>Close this workbook?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            This closes the workbook, charts and forecast in this session. The upload stays under Recent uploads on the server, and the original file on your computer is not affected.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmClear(false)}>Cancel</Button>
          <Button
            color="error"
            variant="contained"
            onClick={() => {
              dispatch(clearSalesData());
              setConfirmClear(false);
              notify('Workbook closed', 'info');
            }}
          >
            Close workbook
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
