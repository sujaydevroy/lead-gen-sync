'use client';

import { useRef, useState } from 'react';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import CloudUploadOutlinedIcon from '@mui/icons-material/CloudUploadOutlined';
import DownloadRoundedIcon from '@mui/icons-material/DownloadRounded';
import StorefrontRoundedIcon from '@mui/icons-material/StorefrontRounded';
import PageHeader from '@/components/ui/PageHeader';
import SectionCard from '@/components/ui/SectionCard';
import DealerUploadSummary from '@/components/admin/DealerUploadSummary';
import { useNotify } from '@/components/providers/NotificationProvider';
import useAsync from '@/hooks/useAsync';
import adminService, { DEALER_FILE_EXTENSIONS } from '@/services/adminService';
import { formatNumber } from '@/lib/format';

/**
 * Dealer files go into the dealer directory (dcp.dealers): dealer data only, owned by no company. Clients are
 * matched to dealers through the products they deal in.
 */
export default function DealerUploadPage() {
  const notify = useNotify();
  const input = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const directory = useAsync(() => adminService.getDealerDirectory(), []);

  const upload = async (file) => {
    if (!file) return;
    setError('');
    setResult(null);
    setUploading(true);
    try {
      const outcome = await adminService.uploadDealers(file);
      setResult(outcome);
      notify(`${outcome.inserted} new and ${outcome.updated} updated dealer(s) saved to the dealer directory`, outcome.failed ? 'warning' : 'success');
      directory.reload();
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
        subtitle="Add or update dealers in the dealer directory from an Excel (.xlsx, .xls), CSV or JSON file"
        meta={
          <Chip
            icon={<StorefrontRoundedIcon />}
            label={directory.data ? `${formatNumber(directory.data.dealerCount)} dealers in the directory` : 'Dealer directory'}
            variant="outlined"
          />
        }
        actions={
          <Button component="a" href={adminService.dealerTemplateUrl()} variant="outlined" startIcon={<DownloadRoundedIcon />}>
            Download template
          </Button>
        }
      />

      <Stack spacing={3}>
        <SectionCard
          title="Upload a dealer file"
          subtitle="Dealers belong to no company; clients are matched to them through the products they deal in"
        >
          <Stack spacing={2.5}>
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
                    .xlsx, .xls, .csv or .json (a list like dealers.json), max 10 MB. Columns: Dealer ID, Dealer Name, Company
                    Name, Dealer Type, Status, Contact Person, Email, Phone, Website, Registration No, Full Address, City, State,
                    Postal Code, Country, Region, Sector, Products, Last Transaction Date / Amount, Currency, Source URL,
                    Verification Date. New dealers need Dealer Name, Dealer Type and Country; a Dealer ID that already exists
                    updates that dealer, an empty Dealer ID gets a new DLR code.
                  </Typography>
                  <Button variant="contained" startIcon={<CloudUploadOutlinedIcon />} onClick={() => input.current?.click()}>
                    Browse files
                  </Button>
                </Stack>
              )}
            </Box>
            {error && <Alert severity="error">{error}</Alert>}
          </Stack>
        </SectionCard>

        {result && (
          <SectionCard title={`Result: ${result.fileName}`} subtitle="Saved to the dealer directory">
            <DealerUploadSummary upload={result} />
          </SectionCard>
        )}
      </Stack>
    </>
  );
}
