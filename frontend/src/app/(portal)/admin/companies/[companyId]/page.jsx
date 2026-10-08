'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useForm } from 'react-hook-form';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import Skeleton from '@mui/material/Skeleton';
import CircularProgress from '@mui/material/CircularProgress';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogActions from '@mui/material/DialogActions';
import ArrowBackRoundedIcon from '@mui/icons-material/ArrowBackRounded';
import DriveFolderUploadRoundedIcon from '@mui/icons-material/DriveFolderUploadRounded';
import BlockRoundedIcon from '@mui/icons-material/BlockRounded';
import RestoreRoundedIcon from '@mui/icons-material/RestoreRounded';
import PageHeader from '@/components/ui/PageHeader';
import SectionCard from '@/components/ui/SectionCard';
import StatCard from '@/components/ui/StatCard';
import StatusBadge from '@/components/ui/StatusBadge';
import EmptyState from '@/components/ui/EmptyState';
import CompanyFormFields, { EMPTY_COMPANY, companyToForm, formToPayload } from '@/components/admin/CompanyFormFields';
import UserTable from '@/components/admin/UserTable';
import { useNotify } from '@/components/providers/NotificationProvider';
import useAsync from '@/hooks/useAsync';
import adminService from '@/services/adminService';
import { formatDate, formatNumber } from '@/lib/format';

export default function CompanyAdminPage() {
  const { companyId } = useParams();
  const code = decodeURIComponent(companyId);
  const notify = useNotify();
  const [company, setCompany] = useState(null);
  const [confirming, setConfirming] = useState(false);
  const [toggling, setToggling] = useState(false);
  const loaded = useAsync(() => adminService.getCompany(code), [code]);
  const users = useAsync(() => adminService.getCompanyUsers(code), [code]);
  const { data: lookups } = useAsync(() => adminService.getLookups(), []);

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting, isDirty },
  } = useForm({ defaultValues: EMPTY_COMPANY });

  useEffect(() => {
    if (loaded.data) {
      setCompany(loaded.data);
      reset(companyToForm(loaded.data));
    }
  }, [loaded.data, reset]);

  const onSubmit = async (values) => {
    try {
      const updated = await adminService.updateCompany(code, formToPayload(values));
      setCompany(updated);
      reset(companyToForm(updated));
      notify('Company details saved', 'success');
    } catch (error) {
      notify(error.message, 'error');
    }
  };

  const toggleActive = async () => {
    setToggling(true);
    try {
      const updated = company.isActive ? await adminService.deactivateCompany(code) : await adminService.activateCompany(code);
      setCompany(updated);
      notify(updated.isActive ? `${updated.name} is active again` : `${updated.name} was deactivated`, updated.isActive ? 'success' : 'info');
      setConfirming(false);
    } catch (error) {
      notify(error.message, 'error');
    } finally {
      setToggling(false);
    }
  };

  const back = (
    <Button component={Link} href="/admin/companies" startIcon={<ArrowBackRoundedIcon />} color="inherit" sx={{ mb: 1.5 }}>
      All companies
    </Button>
  );

  if (loaded.error) {
    return (
      <>
        {back}
        <Card>
          <EmptyState
            variant="error"
            title={loaded.error.status === 404 ? 'Company not found' : 'The company could not be loaded'}
            description={loaded.error.message}
            actionLabel={loaded.error.status === 404 ? undefined : 'Retry'}
            onAction={loaded.reload}
          />
        </Card>
      </>
    );
  }
  if (!company) {
    return (
      <>
        {back}
        <Skeleton height={64} width={360} />
        <Skeleton variant="rounded" height={420} sx={{ mt: 2 }} />
      </>
    );
  }

  return (
    <>
      {back}
      <PageHeader
        title={company.name}
        subtitle={`Company ID ${company.id} · created ${formatDate(company.createdOn)}`}
        meta={<StatusBadge status={company.isActive ? 'Active' : 'Inactive'} />}
        actions={
          <>
            <Button
              component={Link}
              href={`/admin/dealer-uploads?company=${encodeURIComponent(company.id)}`}
              variant="outlined"
              startIcon={<DriveFolderUploadRoundedIcon />}
              disabled={!company.isActive}
            >
              Upload dealers
            </Button>
            <Button
              variant="outlined"
              color={company.isActive ? 'error' : 'success'}
              startIcon={company.isActive ? <BlockRoundedIcon /> : <RestoreRoundedIcon />}
              onClick={() => (company.isActive ? setConfirming(true) : toggleActive())}
              disabled={toggling}
            >
              {company.isActive ? 'Deactivate' : 'Activate'}
            </Button>
          </>
        }
      />

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 6, md: 3 }}>
          <StatCard label="Users" value={formatNumber(company.userCount)} />
        </Grid>
        <Grid size={{ xs: 6, md: 3 }}>
          <StatCard label="Dealers" value={formatNumber(company.dealerCount)} />
        </Grid>
      </Grid>

      <Stack spacing={3}>
        <SectionCard title="Company details" subtitle="Shown to the company's users on their Company Details page">
          <Box component="form" onSubmit={handleSubmit(onSubmit)} noValidate>
            <CompanyFormFields register={register} control={control} errors={errors} lookups={lookups} />
            <Stack direction="row" spacing={1} sx={{ justifyContent: 'flex-end', mt: 3 }}>
              <Button color="inherit" disabled={!isDirty || isSubmitting} onClick={() => reset(companyToForm(company))}>
                Discard
              </Button>
              <Button
                type="submit"
                variant="contained"
                disabled={!isDirty || isSubmitting}
                startIcon={isSubmitting ? <CircularProgress size={16} color="inherit" /> : null}
              >
                {isSubmitting ? 'Saving…' : 'Save changes'}
              </Button>
            </Stack>
          </Box>
        </SectionCard>

        <SectionCard
          title="Users"
          subtitle="Read-only here: the company's own administrators add users and change roles or status"
          noPadding
        >
          {users.error ? (
            <Typography variant="body2" color="error" sx={{ p: 2.5 }}>
              Users could not be loaded.
            </Typography>
          ) : users.loading && !users.data ? (
            <Box sx={{ p: 2 }}>
              <Skeleton height={44} />
            </Box>
          ) : (
            <UserTable users={users.data} />
          )}
        </SectionCard>
      </Stack>

      <Dialog open={confirming} onClose={() => !toggling && setConfirming(false)}>
        <DialogTitle>Deactivate {company.name}?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Its {formatNumber(company.userCount)} user(s) will be signed out and can no longer sign in. Dealers, messages and
            sales data are kept, and you can activate the company again at any time.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button color="inherit" onClick={() => setConfirming(false)} disabled={toggling}>
            Cancel
          </Button>
          <Button color="error" variant="contained" onClick={toggleActive} disabled={toggling}>
            {toggling ? 'Deactivating…' : 'Deactivate'}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
