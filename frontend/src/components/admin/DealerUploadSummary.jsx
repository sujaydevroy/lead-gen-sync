'use client';

import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Chip from '@mui/material/Chip';
import Alert from '@mui/material/Alert';
import Typography from '@mui/material/Typography';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import StatCard from '@/components/ui/StatCard';
import { formatNumber } from '@/lib/format';

/** Outcome of one dealer file: counts, recognised / ignored columns and the rows that were not saved. */
export default function DealerUploadSummary({ upload }) {
  const columns = Object.entries(upload.columnMapping || {});
  const created = Object.entries(upload.createdLookups || {});
  return (
    <Stack spacing={2.5}>
      <Grid container spacing={2}>
        {[
          ['Rows in file', upload.totalRows],
          ['New dealers', upload.inserted],
          ['Updated dealers', upload.updated],
          ['Rows with errors', upload.failed],
        ].map(([label, value]) => (
          <Grid key={label} size={{ xs: 6, md: 3 }}>
            <StatCard label={label} value={formatNumber(value)} />
          </Grid>
        ))}
      </Grid>

      {upload.failed === 0 ? (
        <Alert severity="success">Every row was saved to the dealer directory.</Alert>
      ) : (
        <Alert severity={upload.inserted + upload.updated ? 'warning' : 'error'}>
          {formatNumber(upload.inserted + upload.updated)} row(s) were saved. {formatNumber(upload.failed)} row(s) were skipped —
          fix them in the file and upload it again (existing Dealer IDs are updated, not duplicated).
        </Alert>
      )}

      {created.length > 0 && (
        <Alert severity="info">
          <Typography variant="body2" gutterBottom>
            New values were added to the lists (check them for typos):
          </Typography>
          {created.map(([kind, values]) => (
            <Typography key={kind} variant="body2">
              <strong>{kind}:</strong> {values.join(', ')}
            </Typography>
          ))}
        </Alert>
      )}

      {upload.sourcesSaved > 0 && (
        <Typography variant="body2" color="text.secondary">
          {formatNumber(upload.sourcesSaved)} dealer source link(s) saved.
        </Typography>
      )}

      {columns.length > 0 && (
        <Box>
          <Typography variant="subtitle2" gutterBottom>
            Columns used
          </Typography>
          <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 0.75 }}>
            {columns.map(([field, header]) => (
              <Chip key={field} size="small" variant="outlined" label={header} />
            ))}
            {(upload.ignoredColumns || []).map((header) => (
              <Chip key={`ignored-${header}`} size="small" label={`${header} (ignored)`} sx={{ textDecoration: 'line-through' }} />
            ))}
          </Stack>
        </Box>
      )}

      {upload.issues?.length > 0 && (
        <Box>
          <Typography variant="subtitle2" gutterBottom>
            Rows that were not saved{upload.issues.length < upload.failed ? ` (first ${formatNumber(upload.issues.length)})` : ''}
          </Typography>
          <TableContainer sx={{ maxHeight: 360, border: 1, borderColor: 'divider', borderRadius: 2 }}>
            <Table size="small" stickyHeader aria-label="Rows with errors">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ width: 90 }}>Row</TableCell>
                  <TableCell>Problem</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {upload.issues.map((issue) => (
                  <TableRow key={`${issue.row}-${issue.message}`}>
                    <TableCell>{issue.row}</TableCell>
                    <TableCell>{issue.message}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      )}
    </Stack>
  );
}
