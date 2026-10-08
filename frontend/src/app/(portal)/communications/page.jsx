'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Paper from '@mui/material/Paper';
import Table from '@mui/material/Table';
import TableHead from '@mui/material/TableHead';
import TableBody from '@mui/material/TableBody';
import TableRow from '@mui/material/TableRow';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TablePagination from '@mui/material/TablePagination';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import Autocomplete from '@mui/material/Autocomplete';
import TextField from '@mui/material/TextField';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Skeleton from '@mui/material/Skeleton';
import EditRoundedIcon from '@mui/icons-material/EditRounded';
import PageHeader from '@/components/ui/PageHeader';
import EmptyState from '@/components/ui/EmptyState';
import DealerSearchField from '@/components/dealers/DealerSearchField';
import ContactDealerDialog from '@/components/communication/ContactDealerDialog';
import CommunicationHistory, { TYPE_ICONS } from '@/components/communication/CommunicationHistory';
import communicationService from '@/services/communicationService';
import { useNotify } from '@/components/providers/NotificationProvider';
import dealerService from '@/services/dealerService';
import useAsync from '@/hooks/useAsync';
import useDebounce from '@/hooks/useDebounce';
import { COMMUNICATION_TYPES } from '@/types/communication';
import { formatDate } from '@/lib/format';

export default function CommunicationsPage() {
  const [search, setSearch] = useState('');
  const [types, setTypes] = useState([]);
  const [direction, setDirection] = useState('');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(20);
  const [selected, setSelected] = useState(null);
  const [composeOpen, setComposeOpen] = useState(false);
  const [contactDealer, setContactDealer] = useState(null);

  const notify = useNotify();
  // Server-side pagination (page is 0-based in the table, 1-based in the API).
  const { data, loading, error, reload } = useAsync(
    () => communicationService.getCommunicationsPage({ search, types, direction, page: page + 1, pageSize: rowsPerPage }),
    [search, types.join(','), direction, page, rowsPerPage],
  );
  useEffect(() => communicationService.subscribe(reload), [reload]);

  const rows = data?.items || [];
  const pageRows = rows;

  const reply = async (communication) => {
    setSelected(null);
    try {
      setContactDealer(await dealerService.getDealerById(communication.dealerId));
    } catch (err) {
      notify(err.message || 'The dealer could not be loaded.', 'error');
    }
  };

  return (
    <>
      <PageHeader
        title="Communications"
        subtitle="Every message, email, call and meeting with your dealers"
        actions={
          <Button variant="contained" startIcon={<EditRoundedIcon />} onClick={() => setComposeOpen(true)}>
            New message
          </Button>
        }
      />

      <Paper variant="outlined" sx={{ borderRadius: 3, overflow: 'hidden' }}>
        <Stack direction={{ xs: 'column', lg: 'row' }} spacing={1.5} sx={{ p: 2, alignItems: { lg: 'center' } }}>
          <Box sx={{ flexGrow: 1 }}>
            <DealerSearchField
              value={search}
              onSearch={(v) => {
                setSearch(v);
                setPage(0);
              }}
              placeholder="Search by subject, dealer, sender or message..."
            />
          </Box>
          <ToggleButtonGroup
            size="small"
            value={types}
            onChange={(_, v) => {
              setTypes(v);
              setPage(0);
            }}
            aria-label="Communication type"
            sx={{ flexWrap: 'wrap' }}
          >
            {COMMUNICATION_TYPES.map((t) => (
              <ToggleButton key={t} value={t}>
                {t}
              </ToggleButton>
            ))}
          </ToggleButtonGroup>
          <ToggleButtonGroup
            size="small"
            exclusive
            value={direction}
            onChange={(_, v) => {
              setDirection(v ?? '');
              setPage(0);
            }}
            aria-label="Direction"
          >
            <ToggleButton value="">All</ToggleButton>
            <ToggleButton value="outbound">Sent</ToggleButton>
            <ToggleButton value="inbound">Received</ToggleButton>
          </ToggleButtonGroup>
        </Stack>

        {error ? (
          <EmptyState variant="error" title="Unable to load communications." description="Please try again." actionLabel="Retry" onAction={reload} />
        ) : loading && !data ? (
          <Box sx={{ p: 2 }}>
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} height={48} />
            ))}
          </Box>
        ) : !rows.length ? (
          <EmptyState
            title="No communications found"
            description="Try a different search or clear the type and direction filters."
            actionLabel="Clear filters"
            onAction={() => {
              setSearch('');
              setTypes([]);
              setDirection('');
            }}
          />
        ) : (
          <>
            <TableContainer>
              <Table sx={{ minWidth: { md: 860 } }} aria-label="Communications">
                <TableHead>
                  <TableRow>
                    <TableCell>Date</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell>Dealer</TableCell>
                    <TableCell sx={{ display: { xs: 'none', md: 'table-cell' } }}>Sender → Recipient</TableCell>
                    <TableCell>Subject</TableCell>
                    <TableCell>Status</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {pageRows.map((c) => {
                    const Icon = TYPE_ICONS[c.type];
                    return (
                      <TableRow key={c.id} hover sx={{ cursor: 'pointer' }} onClick={() => setSelected(c)}>
                        <TableCell sx={{ whiteSpace: 'nowrap' }}>
                          <Typography variant="body2">{formatDate(c.createdAt)}</Typography>
                          <Typography variant="caption">{new Date(c.createdAt).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}</Typography>
                        </TableCell>
                        <TableCell>
                          <Chip size="small" icon={<Icon />} label={c.type} variant="outlined" />
                        </TableCell>
                        <TableCell>
                          <Typography
                            component={Link}
                            href={`/dealers/${c.dealerId}`}
                            onClick={(e) => e.stopPropagation()}
                            variant="body2"
                            sx={{ fontWeight: 600, color: 'primary.main', textDecoration: 'none' }}
                          >
                            {c.dealerName || c.dealerId}
                          </Typography>
                        </TableCell>
                        <TableCell sx={{ display: { xs: 'none', md: 'table-cell' } }}>
                          <Typography variant="body2">{c.sender}</Typography>
                          <Typography variant="caption">→ {c.recipient}</Typography>
                        </TableCell>
                        <TableCell sx={{ maxWidth: 280 }}>
                          <Typography variant="body2" noWrap title={c.subject}>
                            {c.subject}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" sx={{ color: c.direction === 'inbound' ? 'primary.main' : 'success.main', fontWeight: 600 }}>
                            {c.status}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </TableContainer>
            <TablePagination
              component="div"
              count={data?.total ?? 0}
              page={page}
              onPageChange={(_, p) => setPage(p)}
              rowsPerPage={rowsPerPage}
              onRowsPerPageChange={(e) => {
                setRowsPerPage(Number(e.target.value));
                setPage(0);
              }}
              rowsPerPageOptions={[10, 20, 50]}
            />
          </>
        )}
      </Paper>

      <Dialog open={Boolean(selected)} onClose={() => setSelected(null)} fullWidth maxWidth="sm">
        <DialogTitle>Communication details</DialogTitle>
        <DialogContent dividers>{selected && <CommunicationHistory items={[selected]} showDealer />}</DialogContent>
        <DialogActions>
          {selected && (
            <Button component={Link} href={`/dealers/${selected.dealerId}?tab=communication`}>
              Open dealer
            </Button>
          )}
          <Button
            variant="contained"
            onClick={() => reply(selected)}
          >
            Reply
          </Button>
        </DialogActions>
      </Dialog>

      <ComposeDialog
        open={composeOpen}
        onClose={() => setComposeOpen(false)}
        onPick={(dealer) => {
          setComposeOpen(false);
          setContactDealer(dealer);
        }}
      />
      <ContactDealerDialog dealer={contactDealer} open={Boolean(contactDealer)} onClose={() => setContactDealer(null)} />
    </>
  );
}

function ComposeDialog({ open, onClose, onPick }) {
  const [input, setInput] = useState('');
  const term = useDebounce(input, 250);
  const [value, setValue] = useState(null);
  const options = useAsync(() => (open ? dealerService.searchDealers(term, 25) : Promise.resolve([])), [term, open]);

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>New message</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Choose the dealer you want to contact.
        </Typography>
        <Autocomplete
          value={value}
          onChange={(_, v) => setValue(v)}
          inputValue={input}
          onInputChange={(_, v) => setInput(v)}
          options={options.data || []}
          loading={options.loading}
          filterOptions={(x) => x}
          getOptionLabel={(d) => `${d.dealer_name} (${d.dealer_id})`}
          isOptionEqualToValue={(a, b) => a.dealer_id === b.dealer_id}
          renderOption={(props, d) => {
            const { key, ...rest } = props;
            return (
              <li key={key} {...rest}>
                <Box>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    {d.dealer_name}
                  </Typography>
                  <Typography variant="caption">
                    {d.dealer_id} · {d.city}, {d.country} · {d.email}
                  </Typography>
                </Box>
              </li>
            );
          }}
          renderInput={(params) => <TextField {...params} label="Dealer" placeholder="Search by name, ID, city or email" autoFocus />}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" disabled={!value} onClick={() => onPick(value)}>
          Continue
        </Button>
      </DialogActions>
    </Dialog>
  );
}
