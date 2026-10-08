'use client';

import { useState } from 'react';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Skeleton from '@mui/material/Skeleton';
import Button from '@mui/material/Button';
import CategoryOutlinedIcon from '@mui/icons-material/CategoryOutlined';
import EditOutlinedIcon from '@mui/icons-material/EditOutlined';
import PageHeader from '@/components/ui/PageHeader';
import SectionCard from '@/components/ui/SectionCard';
import InfoGrid from '@/components/ui/InfoGrid';
import EntityAvatar from '@/components/ui/EntityAvatar';
import EmptyState from '@/components/ui/EmptyState';
import CountryLabel from '@/components/ui/CountryLabel';
import EditCompanyDialog from '@/components/company/EditCompanyDialog';
import { useNotify } from '@/components/providers/NotificationProvider';
import { useAuth } from '@/components/providers/AuthProvider';
import companyService from '@/services/companyService';
import useAsync from '@/hooks/useAsync';
import useCompanySector from '@/hooks/useCompanySector';
import { formatNumber } from '@/lib/format';
import { isCompanyAdmin } from '@/lib/roles';

export default function CompanyPage() {
  const { user, updateCompany } = useAuth();
  const notify = useNotify();
  const loaded = useAsync(() => companyService.getCompanyDetails(), [user.companyId]);
  const { loading, error, reload } = loaded;
  const [saved, setSaved] = useState(null); // details returned by the last edit
  const [editing, setEditing] = useState(false);
  const company = saved ?? loaded.data;
  const sectorDefinition = useCompanySector();
  const canEdit = isCompanyAdmin(user);

  const onSaved = (updated) => {
    setSaved(updated);
    updateCompany(updated);
    setEditing(false);
    notify('Company details saved', 'success');
  };

  if (error) {
    return (
      <Card>
        <EmptyState variant="error" title="Unable to load company details." description="Please try again." actionLabel="Retry" onAction={reload} />
      </Card>
    );
  }

  if (loading || !company) {
    return (
      <>
        <Skeleton width={260} height={48} />
        <Skeleton variant="rounded" height={140} sx={{ my: 3 }} />
        <Skeleton variant="rounded" height={320} />
      </>
    );
  }

  const { address } = company;

  return (
    <>
      <PageHeader
        title="Company Details"
        subtitle="Information about your organisation used across the portal"
        actions={
          canEdit && (
            <Button variant="contained" startIcon={<EditOutlinedIcon />} onClick={() => setEditing(true)}>
              Edit company
            </Button>
          )
        }
      />

      <Card sx={{ mb: 3 }}>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2.5} sx={{ p: 3, alignItems: { sm: 'center' } }}>
          <EntityAvatar name={company.name} text={company.logoText} size={72} />
          <Box>
            <Typography variant="h5" component="h2">
              {company.name}
            </Typography>
            <Typography color="text.secondary">
              Company ID {company.id} · {company.industry}
            </Typography>
            <Stack direction="row" spacing={1} sx={{ mt: 1.25, flexWrap: 'wrap', rowGap: 1 }}>
              <Chip size="small" color="primary" icon={<CategoryOutlinedIcon />} label={`Sector: ${company.sector}`} />
              <Chip size="small" variant="outlined" label={`${address.country} · ${address.region}`} />
            </Stack>
          </Box>
        </Stack>
      </Card>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, lg: 7 }}>
          <SectionCard title="Company Information">
            <InfoGrid
              items={[
                { label: 'Company name', value: company.name },
                { label: 'Company ID', value: company.id },
                { label: 'Industry', value: company.industry },
                { label: 'Sector', value: company.sector },
                { label: 'Website', value: company.website },
                { label: 'Email', value: company.email },
                { label: 'Phone', value: company.phone },
                { label: 'Registration number', value: company.registrationNumber },
                { label: 'Tax ID', value: company.taxId },
                { label: 'Employees', value: formatNumber(company.employees) },
                { label: 'Founded', value: company.founded },
              ]}
            />
          </SectionCard>
        </Grid>
        <Grid size={{ xs: 12, lg: 5 }}>
          <Stack spacing={3}>
            <SectionCard title="Address">
              <InfoGrid
                items={[
                  { label: 'Address', value: address.line1, full: true },
                  { label: 'City', value: address.city },
                  { label: 'State', value: address.state },
                  { label: 'Postal code', value: address.postalCode },
                  { label: 'Country', value: <CountryLabel country={address.country} /> },
                  { label: 'Region', value: address.region },
                ]}
              />
            </SectionCard>
            <SectionCard
              title="Sector & sub-sectors"
              subtitle="Scopes the Sector and Sub-sector filters on the Dealers page (from sector.json)"
            >
              {sectorDefinition ? (
                <>
                  <Typography variant="subtitle2" sx={{ mb: 1.5 }}>
                    {sectorDefinition.sector} · {sectorDefinition.sub_sectors.length} sub-sectors
                  </Typography>
                  <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 0.75 }}>
                    {sectorDefinition.sub_sectors.map((s) => (
                      <Chip key={s} size="small" label={s} />
                    ))}
                  </Stack>
                </>
              ) : (
                <Typography variant="body2" color="warning.main">
                  The company sector &quot;{company.sector}&quot; was not found in sector.json, so sector filtering is unavailable.
                </Typography>
              )}
            </SectionCard>
          </Stack>
        </Grid>
      </Grid>

      {canEdit && <EditCompanyDialog open={editing} company={company} onClose={() => setEditing(false)} onSaved={onSaved} />}
    </>
  );
}
