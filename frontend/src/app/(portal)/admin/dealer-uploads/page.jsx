'use client';

import { Suspense, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import MenuItem from '@mui/material/MenuItem';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import CloudUploadOutlinedIcon from '@mui/icons-material/CloudUploadOutlined';
import DownloadRoundedIcon from '@mui/icons-material/DownloadRounded';
import PageHeader from '@/components/ui/PageHeader';
import SectionCard from '@/components/ui/SectionCard';
import DealerUploadSummary from '@/components/admin/DealerUploadSummary';
import { useNotify } from '@/components/providers/NotificationProvider';
import useAsync from '@/hooks/useAsync';
import adminService, { DEALER_FILE_EXTENSIONS } from '@/services/adminService';

function DealerUploadWorkspace() {
  const notify = useNotify();
  const params = useSearchParams();
  const input = useRef(null);
  const [companyId, setCompanyId] = useState(params.get('company') || '');
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const companies = useAsync(() => adminService.listCompanies({ includeInactive: false }), []);

  const selected = companies.data?.find((c) => c.id === companyId);

  const upload = async (file) => {
    if (!file) return;
    if (!selected) {
      setError('Choose the company to upload the dealers into first.');
      return;
    }
    setError('');
    setResult(null);
    setUploading(true);
    try {
      const outcome = await adminService.uploadDealers(selected.id, file);
      setResult(outcome);
      notify(`${outcome.inserted} new and ${outcome.updated} updated dealer(s) saved to ${outcome.companyName}`, outcome.failed ? 'warning' : 'success');
      companies.reload();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <>
      <PageHeader
        title="Dealer Upload"
        subtitle="Add or update a company's dealers from an Excel (.xlsx, .xls), CSV or JSON file"
        actions={
          <Button component="a" href={adminService.dealerTemplateUrl()} variant="outlined" startIcon={<DownloadRoundedIcon />}>
            Download template
          </Button>
        }
      />

      <Stack spacing={3}>
        <SectionCard
          title="Upload a dealer file"
          subtitle="Rows are saved straight into the company's dealers. For Excel the first sheet is read and row 1 holds the headers"
        >
          <Stack spacing={2.5}>
            <TextField
              select
              label="Company"
              value={selected ? companyId : ''}
              onChange={(e) => {
                setCompanyId(e.target.value);
                setError('');
              }}
              disabled={uploading || companies.loading}
              helperText={
                companies.error
                  ? 'Companies could not be loaded.'
                  : selected
                    ? `${selected.dealerCount} dealer(s) today · Dealer IDs already in this company are updated`
                    : 'Only active companies are listed'
              }
              error={Boolean(companies.error)}
              sx={{ maxWidth: 520 }}
            >
              {(companies.data || []).map((company) => (
                <MenuItem key={company.id} value={company.id}>
                  {company.name} ({company.id})
                </MenuItem>
              ))}
            </TextField>

            <Box
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragging(false);
                if (!uploading) upload(e.dataTransfer.files?.[0]);
              }}
              sx={{
                border: 2,
                borderStyle: 'dashed',
                borderColor: dragging ? 'primary.main' : 'divider',
                bgcolor: dragging ? 'rgba(31,95,214,0.04)' : 'background.paper',
                borderRadius: 3,
                p: { xs: 3, md: 4 },
                textAlign: 'center',
                transition: 'all .15s',
              }}
            >
              <input
                ref={input}
                type="file"
                hidden
                accept={[...DEALER_FILE_EXTENSIONS, '.xlsm'].join(',')}
                aria-label="Dealer file"
                onChange={(e) => {
                  upload(e.target.files?.[0]);
                  e.target.value = '';
                }}
              />
              {uploading ? (
                <Stack spacing={1.5} sx={{ alignItems: 'center', py: 2 }} role="status">
                  <CircularProgress size={32} />
                  <Typography variant="subtitle1">Reading the file and saving dealers…</Typography>
                </Stack>
              ) : (
                <Stack spacing={1.5} sx={{ alignItems: 'center' }}>
                  <Box sx={{ width: 56, height: 56, borderRadius: '50%', display: 'grid', placeItems: 'center', bgcolor: 'rgba(31,95,214,0.08)', color: 'primary.main' }}>
                    <CloudUploadOutlinedIcon />
                  </Box>
                  <Typography variant="h6">Drag & drop the dealer file here</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 640 }}>
                    .xlsx, .xls, .csv or .json (a list like dealers.json), max 10 MB. Columns: Dealer ID, Dealer Name, Company Name, Dealer Type, Status, Contact
                    Person, Email, Phone, Website, Registration No, Full Address, City, State, Postal Code, Country, Region,
                    Sector, Products, Last Transaction Date / Amount, Currency, Source URL, Verification Date. New dealers need
                    Dealer Name, Dealer Type and Country; leave Dealer ID empty to get a new DLR code.
                  </Typography>
                  <Button variant="contained" startIcon={<CloudUploadOutlinedIcon />} onClick={() => input.current?.click()} disabled={!selected}>
                    Browse files
                  </Button>
                </Stack>
              )}
            </Box>
            {error && <Alert severity="error">{error}</Alert>}
          </Stack>
        </SectionCard>

        {result && (
          <SectionCard title={`Result: ${result.fileName}`} subtitle={`Uploaded into ${result.companyName} (${result.companyId})`}>
            <DealerUploadSummary upload={result} />
          </SectionCard>
        )}
      </Stack>
    </>
  );
}

export default function DealerUploadPage() {
  return (
    <Suspense fallback={null}>
      <DealerUploadWorkspace />
    </Suspense>
  );
}
