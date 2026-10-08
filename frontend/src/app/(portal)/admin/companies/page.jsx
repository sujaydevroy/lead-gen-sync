'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Card from '@mui/material/Card';
import Stack from '@mui/material/Stack';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import InputAdornment from '@mui/material/InputAdornment';
import FormControlLabel from '@mui/material/FormControlLabel';
import Switch from '@mui/material/Switch';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Typography from '@mui/material/Typography';
import Skeleton from '@mui/material/Skeleton';
import AddRoundedIcon from '@mui/icons-material/AddRounded';
import SearchRoundedIcon from '@mui/icons-material/SearchRounded';
import PageHeader from '@/components/ui/PageHeader';
import EmptyState from '@/components/ui/EmptyState';
import EntityAvatar from '@/components/ui/EntityAvatar';
import StatusBadge from '@/components/ui/StatusBadge';
import CreateCompanyDialog from '@/components/admin/CreateCompanyDialog';
import { useNotify } from '@/components/providers/NotificationProvider';
import useAsync from '@/hooks/useAsync';
import useDebounce from '@/hooks/useDebounce';
import adminService from '@/services/adminService';
import { formatDate, formatNumber } from '@/lib/format';

export default function CompaniesPage() {
  const router = useRouter();
  const notify = useNotify();
  const [search, setSearch] = useState('');
  const [showInactive, setShowInactive] = useState(true);
  const [creating, setCreating] = useState(false);
  const query = useDebounce(search, 300);
  const { data: companies, loading, error, reload } = useAsync(
    () => adminService.listCompanies({ search: query, includeInactive: showInactive }),
    [query, showInactive],
  );
  const { data: lookups } = useAsync(() => adminService.getLookups(), []);

  const open = (company) => router.push(`/admin/companies/${encodeURIComponent(company.id)}`);

  return (
    <>
      <PageHeader
        title="Companies"
        subtitle="Customer organizations, their users and dealers"
        actions={
          <Button variant="contained" startIcon={<AddRoundedIcon />} onClick={() => setCreating(true)}>
            New company
          </Button>
        }
      />

      <Card>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ p: 2, alignItems: { sm: 'center' } }}>
          <TextField
            size="small"
            placeholder="Search by name or company ID"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            sx={{ flexGrow: 1, maxWidth: { sm: 420 } }}
            slotProps={{
              input: {
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchRoundedIcon fontSize="small" />
                  </InputAdornment>
                ),
              },
              htmlInput: { 'aria-label': 'Search companies' },
            }}
          />
          <FormControlLabel
            control={<Switch checked={showInactive} onChange={(e) => setShowInactive(e.target.checked)} />}
            label="Show inactive"
          />
        </Stack>

        {error ? (
          <EmptyState variant="error" title="Companies could not be loaded" description={error.message} actionLabel="Retry" onAction={reload} />
        ) : loading && !companies ? (
          <Box sx={{ px: 2, pb: 2 }}>
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} height={56} />
            ))}
          </Box>
        ) : !companies.length ? (
          <EmptyState
            title={query ? 'No companies match your search' : 'No companies yet'}
            description={query ? 'Try another name or company ID.' : 'Create the first customer company.'}
          />
        ) : (
          <TableContainer>
            <Table aria-label="Companies">
              <TableHead>
                <TableRow>
                  <TableCell>Company</TableCell>
                  <TableCell>Sector</TableCell>
                  <TableCell>Location</TableCell>
                  <TableCell align="right">Users</TableCell>
                  <TableCell align="right">Dealers</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Created</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {companies.map((company) => (
                  <TableRow
                    key={company.id}
                    hover
                    onClick={() => open(company)}
                    onKeyDown={(e) => e.key === 'Enter' && open(company)}
                    tabIndex={0}
                    sx={{ cursor: 'pointer', opacity: company.isActive ? 1 : 0.65 }}
                  >
                    <TableCell>
                      <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center' }}>
                        <EntityAvatar name={company.name} text={company.logoText} size={36} />
                        <Box sx={{ minWidth: 0 }}>
                          <Typography variant="subtitle2">{company.name}</Typography>
                          <Typography variant="caption" color="text.secondary">
                            {company.id}
                            {company.industry ? ` · ${company.industry}` : ''}
                          </Typography>
                        </Box>
                      </Stack>
                    </TableCell>
                    <TableCell>{company.sector || '—'}</TableCell>
                    <TableCell>{[company.address?.city, company.address?.country].filter(Boolean).join(', ') || '—'}</TableCell>
                    <TableCell align="right">{formatNumber(company.userCount)}</TableCell>
                    <TableCell align="right">{formatNumber(company.dealerCount)}</TableCell>
                    <TableCell>
                      <StatusBadge status={company.isActive ? 'Active' : 'Inactive'} />
                    </TableCell>
                    <TableCell>{formatDate(company.createdOn)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Card>

      <CreateCompanyDialog
        open={creating}
        lookups={lookups}
        onClose={() => setCreating(false)}
        onCreated={(company) => {
          setCreating(false);
          notify(`${company.name} created (${company.id})`, 'success');
          open(company);
        }}
      />
    </>
  );
}
